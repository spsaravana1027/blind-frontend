/**
 * ============================================================================
 * ESP32-CAM (AI-Thinker OV2640) - Robust Dual-Mode Vision Module
 * ============================================================================
 * Features:
 * 1. AI-Thinker Pin Map with PSRAM high-performance dual buffering.
 * 2. Hardware brownout detector bypass to eliminate power-dip reboots.
 * 3. HTTP Server providing:
 *    - http://<CAM_IP>/capture  -> High-speed JPEG snapshot for Python / OpenCV
 *    - http://<CAM_IP>:81/stream -> Standard MJPEG continuous video stream
 * 4. Dual client fallback: Can also POST frames directly to FastAPI server.
 * 5. Wi-Fi auto-reconnect watchdog & Task Watchdog Timer.
 * 6. Line protocol output to UART (GPIO 1 / GPIO 3) for Main ESP32 integration.
 * ============================================================================
 */

#include <Arduino.h>
#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "esp_http_server.h"
#include "esp_task_wdt.h"
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"
#include "cam_config.h"

// Hardware Timers and State
static unsigned long lastCaptureTime = 0;
static unsigned long lastWiFiCheckTime = 0;
static int camFailCount = 0;
static bool cameraReady = false;

// HTTP Server Handles
static httpd_handle_t camera_httpd = NULL;
static httpd_handle_t stream_httpd = NULL;

#include <Wire.h>

void scanI2C() {
    Wire.begin(SIOD_GPIO_NUM, SIOC_GPIO_NUM);
    Serial.println("\n[I2C BUS TEST] Scanning SDA (Pin 26) and SCL (Pin 27)...");
    byte count = 0;
    for (byte addr = 1; addr < 127; addr++) {
        Wire.beginTransmission(addr);
        if (Wire.endTransmission() == 0) {
            Serial.printf("  >>> FOUND SENSOR AT I2C ADDRESS: 0x%02X <<<\n", addr);
            count++;
        }
    }
    if (count == 0) {
        Serial.println("[I2C BUS TEST] 0 devices found! The camera ribbon pins have no electrical contact with the socket.");
    }
}

// ============================================================================
// CAMERA INITIALIZATION (AI-THINKER PIN MAP)
// ============================================================================
void initCamera() {
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer   = LEDC_TIMER_0;
    config.pin_d0       = Y2_GPIO_NUM;
    config.pin_d1       = Y3_GPIO_NUM;
    config.pin_d2       = Y4_GPIO_NUM;
    config.pin_d3       = Y5_GPIO_NUM;
    config.pin_d4       = Y6_GPIO_NUM;
    config.pin_d5       = Y7_GPIO_NUM;
    config.pin_d6       = Y8_GPIO_NUM;
    config.pin_d7       = Y9_GPIO_NUM;
    config.pin_xclk     = XCLK_GPIO_NUM;
    config.pin_pclk     = PCLK_GPIO_NUM;
    config.pin_vsync    = VSYNC_GPIO_NUM;
    config.pin_href     = HREF_GPIO_NUM;
    config.pin_sccb_sda = SIOD_GPIO_NUM;
    config.pin_sccb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn     = PWDN_GPIO_NUM;
    config.pin_reset    = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;
    config.grab_mode    = CAMERA_GRAB_LATEST;

    if (psramFound()) {
        Serial.printf("[CAM] PSRAM detected (%d KB free). Using QVGA buffer.\n", ESP.getFreePsram() / 1024);
        config.frame_size   = FRAMESIZE_QVGA;
        config.jpeg_quality = 12;
        config.fb_count     = 2;
        config.fb_location  = CAMERA_FB_IN_PSRAM;
    } else {
        Serial.println("[CAM WARNING] No PSRAM detected. Using DRAM buffer.");
        config.frame_size   = FRAMESIZE_QVGA;
        config.jpeg_quality = 15;
        config.fb_count     = 1;
        config.fb_location  = CAMERA_FB_IN_DRAM;
    }

    // Attempt 1: Standard AI-Thinker OV2640 (PWDN 32, 20MHz, JPEG)
    esp_err_t err = esp_camera_init(&config);

    // Attempt 2: PWDN -1 & 10MHz (compatible with clone boards)
    if (err != ESP_OK) {
        Serial.printf("[CAM] Probe 1 failed (0x%x). Trying PWDN=-1 & 10MHz...\n", err);
        esp_camera_deinit();
        delay(150);
        config.pin_pwdn = -1;
        config.xclk_freq_hz = 10000000;
        err = esp_camera_init(&config);
    }

    // Attempt 3: GC2145 / RHYX RGB565 mode
    if (err != ESP_OK) {
        Serial.printf("[CAM] Probe 2 failed (0x%x). Trying GC2145/RGB565 mode...\n", err);
        esp_camera_deinit();
        delay(150);
        config.pin_pwdn = PWDN_GPIO_NUM;
        config.pixel_format = PIXFORMAT_RGB565;
        config.xclk_freq_hz = 10000000;
        err = esp_camera_init(&config);
    }

    // Attempt 4: GC2145 with PWDN=-1
    if (err != ESP_OK) {
        Serial.printf("[CAM] Probe 3 failed (0x%x). Trying GC2145 PWDN=-1...\n", err);
        esp_camera_deinit();
        delay(150);
        config.pin_pwdn = -1;
        config.pixel_format = PIXFORMAT_RGB565;
        config.xclk_freq_hz = 10000000;
        err = esp_camera_init(&config);
    }

    if (err != ESP_OK) {
        Serial.printf("[CAM ERROR] All camera probe attempts failed: 0x%x\n", err);
        cameraReady = false;
        return;
    }

    cameraReady = true;
    Serial.println("[CAM SUCCESS] Camera Sensor detected & initialized successfully!");

    sensor_t * s = esp_camera_sensor_get();
    if (s != NULL) {
        s->set_brightness(s, 1);
        s->set_contrast(s, 1);
        s->set_saturation(s, 0);
    }

    delay(300);
    for (int i = 0; i < 2; i++) {
        camera_fb_t* flush = esp_camera_fb_get();
        if (flush) {
            esp_camera_fb_return(flush);
            delay(50);
        }
    }

    cameraReady = true;
    camFailCount = 0;
    Serial.println("[CAM] OV2640 Camera initialized successfully.");
}

void reinitCamera() {
    Serial.println("[CAM] Reinitializing camera after failure...");
    esp_camera_deinit();
    delay(400);
    initCamera();
}

// ============================================================================
// HTTP SERVER ENDPOINTS: /capture and /stream
// ============================================================================
static esp_err_t capture_handler(httpd_req_t *req) {
    if (!cameraReady) {
        reinitCamera();
    }
    camera_fb_t * fb = esp_camera_fb_get();
    if (!fb) {
        httpd_resp_send_500(req);
        return ESP_FAIL;
    }
    httpd_resp_set_type(req, "image/jpeg");
    httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    esp_err_t res = httpd_resp_send(req, (const char *)fb->buf, fb->len);
    esp_camera_fb_return(fb);
    return res;
}

static esp_err_t stream_handler(httpd_req_t *req) {
    camera_fb_t * fb = NULL;
    esp_err_t res = ESP_OK;
    char part_buf[64];

    res = httpd_resp_set_type(req, _STREAM_CONTENT_TYPE);
    if (res != ESP_OK) return res;

    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

    while (true) {
        fb = esp_camera_fb_get();
        if (!fb) {
            res = ESP_FAIL;
            break;
        }
        size_t hlen = snprintf(part_buf, 64, _STREAM_PART, fb->len);
        res = httpd_resp_send_chunk(req, _STREAM_BOUNDARY, strlen(_STREAM_BOUNDARY));
        if (res == ESP_OK) res = httpd_resp_send_chunk(req, part_buf, hlen);
        if (res == ESP_OK) res = httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len);
        esp_camera_fb_return(fb);
        if (res != ESP_OK) break;
    }
    return res;
}

static esp_err_t index_handler(httpd_req_t *req) {
    const char* html =
        "<!DOCTYPE html><html><head><title>ESP32-CAM Assistive Vision</title></head>"
        "<body style='font-family:sans-serif;text-align:center;background:#1e1e24;color:#fff;padding:20px;'>"
        "<h2>AI Assistive Vision Camera (OV2640)</h2>"
        "<p>Stream Active: <a style='color:#4fc3f7;' href='/stream'>/stream</a> | Snapshot: <a style='color:#4fc3f7;' href='/capture'>/capture</a></p>"
        "<div style='margin-top:15px;'><img src='/stream' style='max-width:100%;border-radius:8px;'/></div>"
        "</body></html>";
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, html, strlen(html));
}

void startCameraServer() {
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port = 80;

    httpd_uri_t index_uri = {
        .uri       = "/",
        .method    = HTTP_GET,
        .handler   = index_handler,
        .user_ctx  = NULL
    };

    httpd_uri_t capture_uri = {
        .uri       = "/capture",
        .method    = HTTP_GET,
        .handler   = capture_handler,
        .user_ctx  = NULL
    };

    if (httpd_start(&camera_httpd, &config) == ESP_OK) {
        httpd_register_uri_handler(camera_httpd, &index_uri);
        httpd_register_uri_handler(camera_httpd, &capture_uri);
        Serial.printf("[HTTP SERVER] Snapshot server listening on port 80: http://%s/capture\n",
                      WiFi.localIP().toString().c_str());
    }

    config.server_port = 81;
    config.ctrl_port = 32769;

    httpd_uri_t stream_uri = {
        .uri       = "/stream",
        .method    = HTTP_GET,
        .handler   = stream_handler,
        .user_ctx  = NULL
    };

    if (httpd_start(&stream_httpd, &config) == ESP_OK) {
        httpd_register_uri_handler(stream_httpd, &stream_uri);
        Serial.printf("[HTTP SERVER] MJPEG video stream listening on port 81: http://%s:81/stream\n",
                      WiFi.localIP().toString().c_str());
    }
}

// ============================================================================
// OPTIONAL CLIENT MODE: Push frames via HTTP POST to FastAPI
// ============================================================================
void sendFrameToServer() {
    if (!cameraReady || WiFi.status() != WL_CONNECTED) return;

    camera_fb_t * fb = esp_camera_fb_get();
    if (!fb) {
        camFailCount++;
        if (camFailCount >= 5) {
            camFailCount = 0;
            reinitCamera();
        }
        return;
    }
    camFailCount = 0;

    HTTPClient http;
    http.setTimeout(2500); // 2.5 second timeout to avoid blocking video thread
    String host = String(SERVER_IP);
    if (host.indexOf(':') != -1 && !host.startsWith("[")) {
        host = "[" + host + "]";
    }
    String serverUrl = "http://" + host + ":" + String(SERVER_PORT) + String(SERVER_PATH);
    http.begin(serverUrl);
    http.addHeader("Content-Type", "image/jpeg");

    int httpCode = http.POST(fb->buf, fb->len);
    if (httpCode == 200) {
        String response = http.getString();
        DynamicJsonDocument doc(2048);
        if (deserializeJson(doc, response) == DeserializationError::Ok && doc.is<JsonArray>()) {
            for (JsonObject obj : doc.as<JsonArray>()) {
                const char* label     = obj["label"] | "unknown";
                float confidence      = obj["confidence"] | 0.0f;
                const char* position  = obj["position"] | "center";
                int clip_id           = obj["clip_id"] | 0;
                const char* tamil     = obj["tamil_text"] | "";

                if (confidence >= CONFIDENCE_THRESHOLD) {
                    // Send UART protocol line to Main ESP32
                    if (strlen(tamil) > 0) {
                        Serial.printf("OBJ,%s,%.2f,%s,%d,%s\n", label, confidence, position, clip_id, tamil);
                    } else {
                        Serial.printf("OBJ,%s,%.2f,%s,%d\n", label, confidence, position, clip_id);
                    }
                }
            }
        }
    }
    http.end();
    esp_camera_fb_return(fb);
}

// ============================================================================
// WIFI INITIALIZATION & AUTO-RECONNECT
// ============================================================================
void initWiFi() {
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    Serial.printf("[CAM WIFI] Connecting to Wi-Fi '%s'...", WIFI_SSID);

    unsigned long start = millis();
    while (WiFi.status() != WL_CONNECTED && (millis() - start) < 12000) {
        delay(400);
        Serial.print(".");
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("\n[CAM WIFI SUCCESS] Connected! IP: %s\n", WiFi.localIP().toString().c_str());
        startCameraServer();
    } else {
        Serial.println("\n[CAM WIFI WARNING] Could not connect within 12 seconds. Will auto-retry in background.");
    }
}

void checkWiFiAutoReconnect() {
    if (millis() - lastWiFiCheckTime >= 10000) {
        lastWiFiCheckTime = millis();
        if (WiFi.status() != WL_CONNECTED) {
            Serial.println("[CAM WIFI] Reconnecting to Wi-Fi...");
            WiFi.reconnect();
        }
    }
}

// ============================================================================
// SETUP & MAIN LOOP
// ============================================================================
void setup() {
    // 1. Disable hardware brownout detector to prevent reboots on power fluctuation
    WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);

    Serial.begin(115200);
    delay(500);

    Serial.println("\n========================================================");
    Serial.println("  ESP32-CAM AI-THINKER VISION MODULE - AUTO-START BOOT");
    Serial.println("========================================================");

    scanI2C();
    initCamera();
    initWiFi();

    // 2. Initialize Task Watchdog Timer (30s threshold)
    esp_task_wdt_init(30, true);
    esp_task_wdt_add(NULL);
}

void loop() {
    // Reset watchdog timer
    esp_task_wdt_reset();

    // Ensure Wi-Fi stays connected
    checkWiFiAutoReconnect();

    // Optional push mode to Python server
    unsigned long now = millis();
    if (now - lastCaptureTime >= CAPTURE_INTERVAL_MS) {
        lastCaptureTime = now;
        #ifndef VISION_MODE_ON_DEVICE
        // Push frame if server IP is configured
        if (WiFi.status() == WL_CONNECTED && strlen(SERVER_IP) > 5) {
            sendFrameToServer();
        }
        #endif
    }

    delay(20);
}
