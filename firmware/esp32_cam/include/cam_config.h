#ifndef CAM_CONFIG_H
#define CAM_CONFIG_H

#include <Arduino.h>

// WiFi Configuration
#ifndef WIFI_SSID
#define WIFI_SSID "Anjana infotech"
#endif

#ifndef WIFI_PASS
#define WIFI_PASS "Anjana@123@"
#endif

// Server Configuration for Mode B (Offloaded YOLOv8 Server)
#define SERVER_IP   "192.168.29.17"  // Laptop's IPv4 address on Wi-Fi 'Varsh'
#define SERVER_PORT 8000
#define SERVER_PATH "/detect"

// Mode Selection: Comment out to use Mode B (Offloaded Server, Default)
// #define VISION_MODE_ON_DEVICE

// Detection Rate Limit (capture interval in ms)
#define CAPTURE_INTERVAL_MS 1000

// Minimum confidence threshold to transmit over UART
#define CONFIDENCE_THRESHOLD 0.50f

// AI-Thinker ESP32-CAM Pin definitions
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27

#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

#endif // CAM_CONFIG_H
