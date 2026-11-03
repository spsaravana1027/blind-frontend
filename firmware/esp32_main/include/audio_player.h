#ifndef AUDIO_PLAYER_H
#define AUDIO_PLAYER_H

#include <Arduino.h>
#include <driver/i2s.h>
#include <SPIFFS.h>
#include "config.h"

// Base Abstract Audio Interface
class AudioPlayerInterface {
public:
    virtual bool begin() = 0;
    virtual void playClip(AudioClip clip, bool isEmergency = false) = 0;
    virtual void playClipIndex(uint16_t clipIndex, bool isEmergency = false) = 0;
    virtual void playTamilText(const char* tamilText, bool isEmergency = false) = 0;
    virtual void playTestTone(uint16_t frequencyHz = 440, uint16_t durationMs = 1000) = 0;
    virtual void stop() = 0;
    virtual void setVolume(uint8_t volume) = 0;
    virtual void update() = 0;
    virtual bool isPlaying() const = 0;
};

// MAX98357A I2S Audio Player Class
class MAX98357AAudioPlayer : public AudioPlayerInterface {
private:
    i2s_port_t i2sPort;
    uint8_t bclkPin;
    uint8_t lrcPin;
    uint8_t dinPin;
    
    bool initialized;
    bool spiffsOk;         // true if SPIFFS mounted successfully
    uint8_t volumePercent;
    
    // Playback state
    bool playing;
    AudioClip currentClip;
    uint16_t lastPlayedClip;
    unsigned long lastPlayedTime;
    unsigned long playStartTime;
    unsigned long clipDurationMs;

    // Queue for pending announcements
    AudioClip pendingClip;
    bool hasPendingClip;
    bool pendingIsEmergency;

    // PCM synth buffer
    static const size_t DMA_BUF_SIZE = 512;
    int16_t sampleBuffer[DMA_BUF_SIZE];

public:
    MAX98357AAudioPlayer(uint8_t bclk = PIN_I2S_BCLK, uint8_t lrc = PIN_I2S_LRC, uint8_t din = PIN_I2S_DIN);
    ~MAX98357AAudioPlayer();

    bool begin() override;
    void playClip(AudioClip clip, bool isEmergency = false) override;
    void playClipIndex(uint16_t clipIndex, bool isEmergency = false) override;
    void playTamilText(const char* tamilText, bool isEmergency = false) override;
    void playTestTone(uint16_t frequencyHz = 440, uint16_t durationMs = 1000) override;
    void stop() override;
    void setVolume(uint8_t volume) override; // 0 - 100%
    void update() override;
    bool isPlaying() const override;

    bool isInitialized() const { return initialized; }
    static const TamilClipMetaData* getTamilMetaData(AudioClip clip);

private:
    // SPIFFS WAV playback (primary path — real Tamil speech)
    bool playWavFromSpiffs(const char* wavPath);

    // Sine-tone fallback (used when WAV file not found in SPIFFS)
    void generateAndWriteAudioSequence(AudioClip clip);
    void writeSineWaveI2S(uint16_t freqHz, uint16_t durationMs, float maxAmplitude = 0.8f);
    void writeHarmonicMelodyI2S(const uint16_t freqs[], const uint16_t durationsMs[], size_t count);
};

// Aliasing for compatibility
typedef MAX98357AAudioPlayer AudioPlayerDFPlayer;

#endif // AUDIO_PLAYER_H
