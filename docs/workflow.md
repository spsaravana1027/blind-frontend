# System Workflow & Architectural Flowcharts

This document provides system flowcharts written in Mermaid diagram format for project reports, documentation, and technical presentations.

---

## 1. System Bootup & Degraded Feature Initialization Flowchart

```mermaid
flowchart TD
    A[Power On / Reset] --> B[Initialize Hardware Pins & Serial Log]
    B --> C{Init I2C MPU6050}
    C -- Success --> D[Set Accel 8G / Gyro 500 deg/s]
    C -- Failed --> E[Log Warning: Enable Simulated MPU Fallback]
    
    D --> F{Init DFPlayer Mini}
    E --> F
    F -- Success --> G[Set Audio Volume 25 / EQ Normal]
    F -- Failed --> H[Log Warning: Enable Audio Simulation Log]
    
    G --> I[Init HC-SR04 & ESP32-CAM Link]
    H --> I
    I --> J{Connect Wi-Fi 3s Timeout}
    J -- Connected --> K[Init Telegram Bot Client]
    J -- Timeout --> L[Log Warning: Enable Offline Queue & Background Reconnect]
    
    K --> M[Play Startup Sound 0001.mp3 & Double Beep]
    L --> M
    M --> N[Enter Continuous Non-Blocking Loop]
```

---

## 2. Multi-Stage Fall Detection State Machine

```mermaid
stateDiagram-v2
    [*] --> IDLE : Power On / Reset
    
    IDLE --> FREEFALL_DETECTED : Accel Mag < 0.45g (Free Fall)
    
    FREEFALL_DETECTED --> IMPACT_DETECTED : Accel Mag > 2.50g within 400ms
    FREEFALL_DETECTED --> IDLE : Timeout > 400ms (False Alarm Drop)
    
    IMPACT_DETECTED --> CHECKING_INACTIVITY : Tilt Angle > 60° within 500ms
    IMPACT_DETECTED --> IDLE : Timeout > 500ms (Impact without Tilt)
    
    CHECKING_INACTIVITY --> FALL_CONFIRMED : Low Motion for 1.2s (User Immobile)
    CHECKING_INACTIVITY --> IDLE : User Motion Detected (Stumble Recovered)
    
    FALL_CONFIRMED --> FALL_COUNTDOWN : Start 15s Alarm & Cancel Window
    
    FALL_COUNTDOWN --> IDLE : User Presses Cancel Button (0015.mp3)
    FALL_COUNTDOWN --> EMERGENCY_ALERT : 15s Countdown Expired
    
    EMERGENCY_ALERT --> EMERGENCY_ALERT : Telegram Alert Sent & Siren Active
```

---

## 3. Object Detection & Obstacle Navigation Pipeline

```mermaid
flowchart LR
    subgraph ESP32-CAM Vision
        CAM[OV2640 Frame Capture] --> POST[HTTP POST /detect to Python Server]
        POST --> YOLO[YOLOv8 Inference + Spatial Calc]
        YOLO --> JSON[JSON: label, confidence, position]
        JSON --> UART_TX[Send UART Line: OBJ,label,conf,pos]
    end

    subgraph ESP32 Main Processing
        UART_TX --> UART_RX[Parse UART Line]
        UART_RX --> CONF_CHK{Confidence >= 0.50?}
        CONF_CHK -- Yes --> MAP[Map Label + Pos to Tamil MP3 Index]
        CONF_CHK -- No --> DISCARD[Discard]

        MAP --> DEBOUNCE{Played in last 4 sec?}
        DEBOUNCE -- No --> QUEUE[Enqueue to Audio Player]
        DEBOUNCE -- Yes --> DISCARD

        QUEUE --> SPK[Play Tamil Voice Prompt via DFPlayer]
    end
```

---

## 4. Telegram Alert & Offline Resiliency Pipeline

```mermaid
flowchart TD
    A[Fall Confirmed & Countdown Expired] --> B[Generate Emergency Payload JSON/Text]
    B --> C{Is Wi-Fi Connected?}
    
    C -- Yes --> D[HTTP POST to Telegram Bot API]
    D --> E{HTTP Status 200 OK?}
    E -- Success --> F[Play 0016.mp3 Telegram Sent Clip]
    E -- Fail --> G[Enqueue Payload into RAM Queue & Increment Retry]
    
    C -- No --> G
    G --> H[Maintain Local Buzzer Siren Alert]
    H --> I[Background Wi-Fi Reconnect Loop]
    I --> J{Wi-Fi Restored?}
    J -- Yes --> K[Flush Enqueued Emergency Alerts to Telegram]
    J -- No --> H
```
