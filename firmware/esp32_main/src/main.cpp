#include <Arduino.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"
#include "state_machine.h"

SystemController sysController;
String serialInputBuffer = "";

void printHelpMenu() {
    Serial.println("\n--- SIMULATION & CLI COMMAND MENU ---");
    Serial.println("  fall                      - Trigger immediate fall down (starts buzzer & sends Telegram)");
    Serial.println("  safe                      - Press safe switch (turns off buzzer & sends safe Telegram)");
    Serial.println("  cancel                    - Alias for safe switch press");
    Serial.println("  med <paracetamol|rantac|tassic> - Trigger medicine voice identification");
    Serial.println("  curr <500|200|100|50|20|10>     - Trigger currency voice identification");
    Serial.println("  obj <label> [pos] [tamil] - Trigger simulated object (e.g. 'obj chair right')");
    Serial.println("  dist <cm>                 - Set simulated distance (e.g. 'dist 45')");
    Serial.println("  medreminder [on|off]      - Enable/disable 15-minute medicine reminder");
    Serial.println("  medtest [on|off]          - Enable/disable 1-minute quick test mode");
    Serial.println("  mednow                    - Trigger immediate medicine reminder alert");
    Serial.println("  i2s [freq] [ms]           - Play MAX98357A I2S test tone (e.g. 'i2s 440 1000')");
    Serial.println("  clip <id>                 - Play Tamil audio clip by ID (e.g. 'clip 30')");
    Serial.println("  status                    - Print system status & diagnostics");
    Serial.println("  help                      - Print this help menu");
    Serial.println("-------------------------------------\n");
}

void processSerialCLI(const String& cmdLine) {
    String cmd = cmdLine;
    cmd.trim();

    if (cmd == "fall") {
        sysController.triggerSimulatedFall();
    } else if (cmd == "safe" || cmd == "cancel") {
        sysController.triggerSimulatedCancel();
    } else if (cmd.startsWith("curr ")) {
        String note = cmd.substring(5);
        note.trim();
        String lbl = note;
        sysController.triggerSimulatedObject(lbl.c_str(), "center", "");
    } else if (cmd.startsWith("med ")) {
        String m = cmd.substring(4);
        m.trim();
        if (m == "on") {
            sysController.setMedicineReminderEnabled(true);
        } else if (m == "off") {
            sysController.setMedicineReminderEnabled(false);
        } else {
            // Medicine identification test
            sysController.triggerSimulatedObject(m.c_str(), "center", "");
        }
    } else if (cmd == "mednow") {
        sysController.playMedicineReminder();
    } else if (cmd.startsWith("medreminder")) {
        if (cmd.endsWith("off")) {
            sysController.setMedicineReminderEnabled(false);
        } else {
            sysController.setMedicineReminderEnabled(true);
        }
    } else if (cmd.startsWith("obj ")) {
        int space1 = cmd.indexOf(' ');
        int space2 = cmd.indexOf(' ', space1 + 1);
        int space3 = cmd.indexOf(' ', space2 + 1);
        
        String label = "";
        String pos = "center";
        String tamilText = "";

        if (space3 != -1) {
            label = cmd.substring(space1 + 1, space2);
            pos = cmd.substring(space2 + 1, space3);
            tamilText = cmd.substring(space3 + 1);
        } else if (space2 != -1) {
            label = cmd.substring(space1 + 1, space2);
            pos = cmd.substring(space2 + 1);
        } else {
            label = cmd.substring(space1 + 1);
        }
        sysController.triggerSimulatedObject(label.c_str(), pos.c_str(), tamilText.c_str());
    } else if (cmd.startsWith("dist ")) {
        float d = cmd.substring(5).toFloat();
        sysController.triggerSimulatedDistance(d);
    } else if (cmd.startsWith("i2s")) {
        uint16_t freq = 440;
        uint16_t dur = 1000;
        int space1 = cmd.indexOf(' ');
        if (space1 != -1) {
            int space2 = cmd.indexOf(' ', space1 + 1);
            if (space2 != -1) {
                freq = cmd.substring(space1 + 1, space2).toInt();
                dur = cmd.substring(space2 + 1).toInt();
            } else {
                freq = cmd.substring(space1 + 1).toInt();
            }
        }
        sysController.triggerI2SAudioTest(freq, dur);
    } else if (cmd.startsWith("clip ")) {
        uint16_t clipId = cmd.substring(5).toInt();
        Serial.printf("[CLI] Playing clip %u on physical speaker...\n", clipId);
        sysController.playClipById(clipId, false);
    } else if (cmd.startsWith("OBJ,")) {
        sysController.processProtocolLine(cmd);
    } else if (cmd == "status") {
        sysController.printStatus();
    } else if (cmd == "help") {
        printHelpMenu();
    } else {
        Serial.printf("[CLI] Unknown command '%s'. Type 'help' for command list.\n", cmd.c_str());
    }
}

void setup() {
    WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); // Disable brownout detector to prevent power dips from resetting ESP32
    Serial.begin(115200);
    delay(500);
    sysController.begin();
    printHelpMenu();
    // Play startup confirmation audio through MAX98357A speaker!
    sysController.playClipById(1, false);
}

void loop() {
    sysController.update();

    // Read CLI input from Serial terminal
    while (Serial.available()) {
        char c = (char)Serial.read();
        if (c == '\n') {
            if (serialInputBuffer.length() > 0) {
                processSerialCLI(serialInputBuffer);
            }
            serialInputBuffer = "";
        } else if (c != '\r') {
            serialInputBuffer += c;
        }
    }
}
