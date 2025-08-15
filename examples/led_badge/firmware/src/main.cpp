#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include <Adafruit_LSM6DS3.h>
#include <Wire.h>
#include <driver/i2s.h>
#include <arduinoFFT.h>
#include <Adafruit_AHRS.h>

// Pin definitions
#define LED_PIN 8
#define BUTTON_PIN 9
#define NUM_LEDS 100
#define MATRIX_WIDTH 10
#define MATRIX_HEIGHT 10
#define SDA_PIN 5
#define SCL_PIN 6

// I2S pins for microphone (from led_badge.ato)
#define I2S_SCK_PIN 0  // i2s.sck - GPIO0
#define I2S_WS_PIN 3   // i2s.ws - GPIO3  
#define I2S_SD_PIN 1   // i2s.sd - GPIO1

// NeoPixel object
Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);

// LSM6DS3 object
Adafruit_LSM6DS3 lsm;

// Modes
#define MODE_RAINBOW 0
#define MODE_BALL 1
#define MODE_LIFE 2
#define MODE_SWEEP 3
#define MODE_CENTER 4
#define MODE_MULTI_BALL 5
#define MODE_LEVEL 6
#define MODE_NYAN 7
#define MODE_SPECTROGRAM 8
#define MODE_VERTICAL_LINE 9
#define MODE_AUDIO_LEVELS 10
#define MODE_BEAT_FLASH 11
int currentMode = MODE_RAINBOW;

// Game of Life
byte grid[MATRIX_HEIGHT][MATRIX_WIDTH] = {0};
byte nextGrid[MATRIX_HEIGHT][MATRIX_WIDTH] = {0};
byte ageGrid[MATRIX_HEIGHT][MATRIX_WIDTH] = {0};
unsigned long lastLifeUpdate = 0;
const unsigned long lifeUpdateInterval = 500; // ms per generation

// Button state
int buttonState = 0;
int lastButtonState = HIGH;
unsigned long lastDebounceTime = 0;
const unsigned long debounceDelay = 50;

// Ball simulation
float singleBallX = MATRIX_WIDTH / 2.0;
float singleBallY = MATRIX_HEIGHT / 2.0;
float singleBallVelX = 0;
float singleBallVelY = 0;
const float gravity = 0.3;
const float friction = 0.99;

// Smoothing for accelerometer
#define SMOOTH_SAMPLES 8
float axHistory[SMOOTH_SAMPLES] = {0};
float ayHistory[SMOOTH_SAMPLES] = {0};
float azHistory[SMOOTH_SAMPLES] = {0};
int smoothIndex = 0;
int smoothCount = 0;
const float sensitivity = 0.5;

Adafruit_Madgwick filter;

unsigned long lastDebugPrint = 0;

// Accelerometer calibration
float offsetX = 0, offsetY = 0, offsetZ = 0;

// LED Matrix mapping function
int getLEDIndex(int x, int y) {
  // Simple linear mapping - LEDs are arranged row by row
  return y * MATRIX_WIDTH + x;
}

// Audio FFT for spectrogram
#define SAMPLES 512
#define SAMPLING_FREQUENCY 16000
#define FFT_BANDS 10 // 10 frequency bands for 10x10 matrix
double vReal[SAMPLES];
double vImag[SAMPLES];
ArduinoFFT<double> FFT = ArduinoFFT<double>(vReal, vImag, SAMPLES, SAMPLING_FREQUENCY);
uint8_t spectrogramData[MATRIX_WIDTH][MATRIX_HEIGHT]; // History of FFT bands

// Beat detection variables
float bassEnergy = 0;
float bassEnergyHistory[20] = {0}; // History for average calculation
int bassHistoryIndex = 0;
bool beatDetected = false;
unsigned long lastBeatTime = 0;
const unsigned long beatCooldown = 100; // Minimum ms between beats
float beatThreshold = 1.5; // Beat detected when current > average * threshold
int beatBrightness = 0; // Current brightness for beat flash
int spectrogramColumn = 0;
unsigned long lastSpectrogramUpdate = 0;
const unsigned long spectrogramInterval = 50; // Update every 50ms
bool i2sConfigured = false;

// Rainbow animation
uint32_t wheel(byte WheelPos)
{
  WheelPos = 255 - WheelPos;
  if (WheelPos < 85)
  {
    return strip.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  }
  if (WheelPos < 170)
  {
    WheelPos -= 85;
    return strip.Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
  WheelPos -= 170;
  return strip.Color(WheelPos * 3, 255 - WheelPos * 3, 0);
}

void rainbowDissolve()
{
  for (int i = 0; i < NUM_LEDS; i++)
  {
    if (random(100) < 10)
    { // 10% chance to change color
      strip.setPixelColor(i, wheel(random(256)));
    }
    else
    {
      uint32_t color = strip.getPixelColor(i);
      uint8_t r = (color >> 16) & 0xFF;
      uint8_t g = (color >> 8) & 0xFF;
      uint8_t b = color & 0xFF;
      r = max(0, r - 1);
      g = max(0, g - 1);
      b = max(0, b - 1);
      strip.setPixelColor(i, strip.Color(r, g, b));
    }
  }
  strip.show();
}

void drawBall()
{
  strip.clear();
  int x = (int)singleBallX;
  int y = (int)singleBallY;
  if (x >= 0 && x < MATRIX_WIDTH && y >= 0 && y < MATRIX_HEIGHT)
  {
    strip.setPixelColor(getLEDIndex(x, y), strip.Color(255, 255, 255));
  }
  strip.show();
}

void updateBall(sensors_event_t accel, sensors_event_t gyro)
{
  // Update Madgwick filter (gyro in rad/s, accel in g)
  float gx = gyro.gyro.x * (PI / 180.0); // deg/s to rad/s
  float gy = gyro.gyro.y * (PI / 180.0);
  float gz = gyro.gyro.z * (PI / 180.0);
  float ax = (accel.acceleration.x - offsetX) / 9.81;
  float ay = (accel.acceleration.y - offsetY) / 9.81;
  float az = (accel.acceleration.z - offsetZ) / 9.81;
  filter.updateIMU(gx, gy, gz, ax, ay, az);

  // Get quaternion
  float w, x, y, z;
  filter.getQuaternion(&w, &x, &y, &z);
  float qw = w;
  float qx = x;
  float qy = y;
  float qz = z;

  // Rotate gravity vector [0,0,-1] by quaternion to get local down
  float gravityX = 2 * (qx * qz - qw * qy);
  float gravityY = -2 * (qw * qx + qy * qz);  // Negated to flip forward/backward
  float gravityZ = qw * qw - qx * qx - qy * qy + qz * qz; // Not used

  // Debug print Euler angles from quaternion
  if (millis() - lastDebugPrint > 100)
  {
    float roll = atan2(2 * (qw * qx + qy * qz), 1 - 2 * (qx * qx + qy * qy)) * 180 / PI;
    float pitch = asin(2 * (qw * qy - qz * qx)) * 180 / PI;
    float yaw = atan2(2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz)) * 180 / PI;
    Serial.print("Roll: ");
    Serial.print(roll);
    Serial.print(" Pitch: ");
    Serial.print(pitch);
    Serial.print(" Yaw: ");
    Serial.print(yaw);
    Serial.print(" | Gx: ");
    Serial.print(gravityX);
    Serial.print(" Gy: ");
    Serial.print(gravityY);
    Serial.println();
    lastDebugPrint = millis();
  }

  // Smoothing on gravity components
  axHistory[smoothIndex] = gravityX;
  ayHistory[smoothIndex] = gravityY;
  smoothIndex = (smoothIndex + 1) % SMOOTH_SAMPLES;
  if (smoothCount < SMOOTH_SAMPLES)
    smoothCount++;

  float avgGx = 0, avgGy = 0;
  for (int i = 0; i < smoothCount; i++)
  {
    avgGx += axHistory[i];
    avgGy += ayHistory[i];
  }
  avgGx /= smoothCount;
  avgGy /= smoothCount;

  singleBallVelX += avgGx * gravity * sensitivity;
  singleBallVelY += avgGy * gravity * sensitivity;

  singleBallVelX *= friction;
  singleBallVelY *= friction;

  singleBallX += singleBallVelX;
  singleBallY += singleBallVelY;

  // Bounce off walls with damping, handle corners by checking velocity direction
  const float bounceDamp = 0.8;
  const float epsilon = 0.001;
  const float minBounceVel = 0.05; // Minimum velocity after bounce

  // Handle X collisions
  if (singleBallX < 0)
  {
    singleBallX = epsilon;
    singleBallVelX = abs(singleBallVelX) * bounceDamp;
    if (singleBallVelX < minBounceVel)
      singleBallVelX = minBounceVel;
  }
  else if (singleBallX >= MATRIX_WIDTH)
  {
    singleBallX = MATRIX_WIDTH - 1 - epsilon;
    singleBallVelX = -abs(singleBallVelX) * bounceDamp;
    if (singleBallVelX > -minBounceVel)
      singleBallVelX = -minBounceVel;
  }

  // Handle Y collisions
  if (singleBallY < 0)
  {
    singleBallY = epsilon;
    singleBallVelY = abs(singleBallVelY) * bounceDamp;
    if (singleBallVelY < minBounceVel)
      singleBallVelY = minBounceVel;
  }
  else if (singleBallY >= MATRIX_HEIGHT)
  {
    singleBallY = MATRIX_HEIGHT - 1 - epsilon;
    singleBallVelY = -abs(singleBallVelY) * bounceDamp;
    if (singleBallVelY > -minBounceVel)
      singleBallVelY = -minBounceVel;
  }
}

void initLife()
{
  for (int y = 0; y < MATRIX_HEIGHT; y++)
  {
    for (int x = 0; x < MATRIX_WIDTH; x++)
    {
      grid[y][x] = random(2); // Random initial state
      ageGrid[y][x] = 0;
    }
  }
}

void updateLife()
{
  for (int y = 0; y < MATRIX_HEIGHT; y++)
  {
    for (int x = 0; x < MATRIX_WIDTH; x++)
    {
      int neighbors = 0;
      for (int dy = -1; dy <= 1; dy++)
      {
        for (int dx = -1; dx <= 1; dx++)
        {
          if (dy == 0 && dx == 0)
            continue;
          int ny = (y + dy + MATRIX_HEIGHT) % MATRIX_HEIGHT;
          int nx = (x + dx + MATRIX_WIDTH) % MATRIX_WIDTH;
          neighbors += grid[ny][nx];
        }
      }
      nextGrid[y][x] = (grid[y][x] == 1 && (neighbors == 2 || neighbors == 3)) || (grid[y][x] == 0 && neighbors == 3);
      if (nextGrid[y][x] == 1)
      {
        if (grid[y][x] == 1)
        {
          ageGrid[y][x]++;
        }
        else
        {
          ageGrid[y][x] = 0; // New birth
        }
      }
    }
  }
  memcpy(grid, nextGrid, sizeof(grid));
}

void drawLife()
{
  strip.clear();
  for (int y = 0; y < MATRIX_HEIGHT; y++)
  {
    for (int x = 0; x < MATRIX_WIDTH; x++)
    {
      if (grid[y][x] == 1)
      {
        byte age = ageGrid[y][x];
        uint8_t r = (age < 4) ? 255 - (age * 64) : 0;
        uint8_t g = (age < 4) ? age * 64 : (age < 8) ? 255 - ((age - 4) * 64)
                                                     : 0;
        uint8_t b = (age >= 4) ? (age - 4) * 64 : 0;
        if (age > 8)
          b = 255;
        strip.setPixelColor(getLEDIndex(x, y), strip.Color(r, g, b));
      }
    }
  }
  strip.show();
}

int currentSweepIndex = 0;
unsigned long lastSweepUpdate = 0;
const unsigned long sweepInterval = 50; // ms per LED

void drawSweep()
{
  for (int i = 0; i < NUM_LEDS; i++)
  {
    uint32_t color = strip.getPixelColor(i);
    uint8_t r = (color >> 16) & 0xFF;
    uint8_t g = (color >> 8) & 0xFF;
    uint8_t b = color & 0xFF;
    r /= 2;
    g /= 2;
    b /= 2;
    strip.setPixelColor(i, strip.Color(r, g, b));
  }
  int y = currentSweepIndex / MATRIX_WIDTH;
  int x = currentSweepIndex % MATRIX_WIDTH;
  strip.setPixelColor(getLEDIndex(x, y), strip.Color(255, 255, 255));
  strip.show();
}

void drawCenter()
{
  strip.clear();
  for (int y = 3; y <= 6; y++)
  { // Center rows 3-6 (0-9 grid)
    for (int x = 3; x <= 6; x++)
    { // Center cols 3-6
      strip.setPixelColor(getLEDIndex(x, y), strip.Color(255, 255, 255)); // Full white
    }
  }
  strip.show();
}

void drawGradient()
{
  strip.clear();
  for (int y = 0; y < MATRIX_HEIGHT; y++)
  {
    for (int x = 0; x < MATRIX_WIDTH; x++)
    {
      uint8_t r = x * 25;       // 0-225
      uint8_t g = y * 25;       // 0-225
      uint8_t b = (x + y) * 12; // 0-228
      strip.setPixelColor(getLEDIndex(x, y), strip.Color(r, g, b));
    }
  }
  strip.show();
}

// Multi-ball mode
#define NUM_BALLS 3
float multiBallX[3], multiBallY[3];
float multiBallVelX[3], multiBallVelY[3];

void initMultiBalls()
{
  for (int i = 0; i < NUM_BALLS; i++)
  {
    multiBallX[i] = random(MATRIX_WIDTH);
    multiBallY[i] = random(MATRIX_HEIGHT);
    multiBallVelX[i] = random(3, 6) / 10.0 * (random(2) ? 1 : -1); // 0.3 to 0.6 speed
    multiBallVelY[i] = random(3, 6) / 10.0 * (random(2) ? 1 : -1);
  }
}

void updateMultiBalls()
{
  const float multiFriction = 0.995;
  const float epsilon = 0.001;
  const float bounceDamp = 0.8;
  for (int i = 0; i < NUM_BALLS; i++)
  {
    multiBallX[i] += multiBallVelX[i];
    multiBallY[i] += multiBallVelY[i];

    // Bounce off walls with damping, handle corners by direction
    if (multiBallX[i] < 0 && multiBallVelX[i] < 0)
    {
      multiBallX[i] = epsilon;
      multiBallVelX[i] = -multiBallVelX[i] * bounceDamp;
    }
    else if (multiBallX[i] >= MATRIX_WIDTH && multiBallVelX[i] > 0)
    {
      multiBallX[i] = MATRIX_WIDTH - 1 - epsilon;
      multiBallVelX[i] = -multiBallVelX[i] * bounceDamp;
    }
    if (multiBallY[i] < 0 && multiBallVelY[i] < 0)
    {
      multiBallY[i] = epsilon;
      multiBallVelY[i] = -multiBallVelY[i] * bounceDamp;
    }
    else if (multiBallY[i] >= MATRIX_HEIGHT && multiBallVelY[i] > 0)
    {
      multiBallY[i] = MATRIX_HEIGHT - 1 - epsilon;
      multiBallVelY[i] = -multiBallVelY[i] * bounceDamp;
    }

    multiBallVelX[i] *= multiFriction;
    multiBallVelY[i] *= multiFriction;
  }
}

void drawMultiBalls()
{
  strip.clear();
  uint32_t colors[NUM_BALLS] = {strip.Color(255, 0, 0), strip.Color(0, 255, 0), strip.Color(0, 0, 255)};
  for (int i = 0; i < NUM_BALLS; i++)
  {
    int x = (int)multiBallX[i];
    int y = (int)multiBallY[i];
    strip.setPixelColor(getLEDIndex(x, y), colors[i]);
  }
  strip.show();
}

// Level mode
void drawLevel(float gx, float gy)
{
  strip.clear();
  int halfW = MATRIX_WIDTH / 2;
  int halfH = MATRIX_HEIGHT / 2;
  const float scale = halfW / 0.087f; // Max at ~5° tilt
  int dx = (int)(gx * scale);
  int dy = (int)(gy * scale);
  int x = constrain(halfW + dx, 0, MATRIX_WIDTH - 1);
  int y = constrain(halfH + dy, 0, MATRIX_HEIGHT - 1);
  strip.setPixelColor(getLEDIndex(x, y), strip.Color(255, 255, 255));
  strip.show();
}

// Nyan Cat mode
int nyanFrame = 0;
unsigned long lastNyanUpdate = 0;
const unsigned long nyanInterval = 200;
const uint8_t nyanFrames[4][10][10] = {/* Simple 4-frame animation data - define colors as RGB bytes, e.g. { {255,0,0, ...} } */}; // Placeholder; fill with actual frame data
void drawNyan()
{
  strip.clear();
  for (int y = 0; y < MATRIX_HEIGHT; y++)
  {
    for (int x = 0; x < MATRIX_WIDTH; x++)
    {
      uint8_t r = nyanFrames[nyanFrame][y][x * 3];
      uint8_t g = nyanFrames[nyanFrame][y][x * 3 + 1];
      uint8_t b = nyanFrames[nyanFrame][y][x * 3 + 2];
      strip.setPixelColor(getLEDIndex(x, y), strip.Color(r, g, b));
    }
  }
  strip.show();
}

// I2S configuration for ICS-43434 microphone
void configureI2S()
{
  if (i2sConfigured)
    return;

  Serial.println("Configuring I2S for microphone...");

  // ICS-43434 outputs data on the left channel when WS is low
  i2s_config_t i2s_config = {
      .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
      .sample_rate = SAMPLING_FREQUENCY,
      .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
      .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT,  // Try both channels
      .communication_format = I2S_COMM_FORMAT_STAND_I2S,
      .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
      .dma_buf_count = 4,
      .dma_buf_len = 512,
      .use_apll = false,
      .tx_desc_auto_clear = false,
      .fixed_mclk = 0};

  i2s_pin_config_t pin_config = {
      .bck_io_num = I2S_SCK_PIN,
      .ws_io_num = I2S_WS_PIN,
      .data_out_num = I2S_PIN_NO_CHANGE,
      .data_in_num = I2S_SD_PIN};

  esp_err_t err = i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL);
  if (err != ESP_OK) {
    Serial.print("Failed to install I2S driver: ");
    Serial.println(err);
    return;
  }
  
  err = i2s_set_pin(I2S_NUM_0, &pin_config);
  if (err != ESP_OK) {
    Serial.print("Failed to set I2S pins: ");
    Serial.println(err);
    return;
  }
  
  err = i2s_set_clk(I2S_NUM_0, SAMPLING_FREQUENCY, I2S_BITS_PER_SAMPLE_32BIT, I2S_CHANNEL_MONO);
  if (err != ESP_OK) {
    Serial.print("Failed to set I2S clock: ");
    Serial.println(err);
    return;
  }

  Serial.println("I2S configured successfully!");
  i2sConfigured = true;
}

void readAudioData()
{
  size_t bytes_read = 0;
  int32_t i2s_read_buff[SAMPLES];

  esp_err_t result = i2s_read(I2S_NUM_0, (void *)i2s_read_buff, sizeof(i2s_read_buff), &bytes_read, portMAX_DELAY);
  
  if (result != ESP_OK) {
    Serial.print("I2S read error: ");
    Serial.println(result);
    return;
  }

  // Debug: Calculate average and peak values
  int32_t sum = 0;
  int32_t peak = 0;
  int32_t min_val = INT32_MAX;
  int32_t max_val = INT32_MIN;
  int non_zero_count = 0;
  
  // Convert 32-bit samples to doubles for FFT
  // With RIGHT_LEFT format, we get interleaved stereo data
  int fft_index = 0;
  for (int i = 0; i < bytes_read/sizeof(int32_t) && fft_index < SAMPLES; i++)
  {
    int32_t sample = i2s_read_buff[i];
    if (sample != 0) non_zero_count++;
    
    sum += abs(sample);
    if (abs(sample) > peak) peak = abs(sample);
    if (sample < min_val) min_val = sample;
    if (sample > max_val) max_val = sample;
    
    // Only use left channel samples (every other sample)
    if (i % 2 == 0) {
      // ICS-43434 outputs 24-bit data in 32-bit frame
      // The data appears to be in the upper bits, so shift right to normalize
      vReal[fft_index] = (double)(sample >> 16); // Scale to 16-bit range for FFT
      vImag[fft_index] = 0.0;
      fft_index++;
    }
  }
  
  // Fill remaining FFT buffer if needed
  while (fft_index < SAMPLES) {
    vReal[fft_index] = 0.0;
    vImag[fft_index] = 0.0;
    fft_index++;
  }
  
  // Print debug info every 500ms
  static unsigned long lastDebugMic = 0;
  if (millis() - lastDebugMic > 500) {
    int32_t avg = sum / SAMPLES;
    Serial.print("Mic - Bytes: ");
    Serial.print(bytes_read);
    Serial.print(" Avg: ");
    Serial.print(avg);
    Serial.print(" Peak: ");
    Serial.print(peak);
    Serial.print(" Min: ");
    Serial.print(min_val);
    Serial.print(" Max: ");
    Serial.print(max_val);
    Serial.print(" NonZero: ");
    Serial.print(non_zero_count);
    
    // Print first few raw samples
    Serial.print(" Raw[0-4]: ");
    for (int i = 0; i < 5; i++) {
      Serial.print(i2s_read_buff[i], HEX);
      Serial.print(" ");
    }
    Serial.println();
    
    lastDebugMic = millis();
  }
}

void updateSpectrogram()
{
  readAudioData();

  // Apply window function
  FFT.windowing(FFT_WIN_TYP_HAMMING, FFT_FORWARD);

  // Compute FFT
  FFT.compute(FFT_FORWARD);

  // Compute magnitudes
  FFT.complexToMagnitude();

  // Map FFT bins to 10 frequency bands
  double bandValues[FFT_BANDS] = {0};
  int binsPerBand = (SAMPLES / 2) / FFT_BANDS;

  for (int band = 0; band < FFT_BANDS; band++)
  {
    double maxVal = 0;
    for (int bin = band * binsPerBand; bin < (band + 1) * binsPerBand; bin++)
    {
      if (vReal[bin] > maxVal)
      {
        maxVal = vReal[bin];
      }
    }
    // Logarithmic scaling and normalization
    // Adjust scaling factor based on observed data range
    if (maxVal > 1) {  // Threshold to filter out noise
      // More aggressive scaling for better sensitivity
      bandValues[band] = log10(maxVal) * 40 + 50; // Increased scaling and offset
      if (bandValues[band] > 255)
        bandValues[band] = 255;
    } else {
      bandValues[band] = 0;
    }
  }

  // Store in spectrogram history
  for (int i = 0; i < FFT_BANDS; i++)
  {
    spectrogramData[spectrogramColumn][i] = (uint8_t)bandValues[i];
  }

  // Debug: Print FFT band values every 500ms
  static unsigned long lastDebugFFT = 0;
  if (millis() - lastDebugFFT > 500) {
    Serial.print("FFT Bands: ");
    for (int i = 0; i < FFT_BANDS; i++) {
      Serial.print((int)bandValues[i]);
      Serial.print(" ");
    }
    Serial.println();
    lastDebugFFT = millis();
  }

  // Move to next column
  spectrogramColumn = (spectrogramColumn + 1) % MATRIX_WIDTH;
}

void drawSpectrogram()
{
  strip.clear();

  for (int x = 0; x < MATRIX_WIDTH; x++)
  {
    for (int y = 0; y < MATRIX_HEIGHT; y++)
    {
      // Get historical data with proper wrapping
      int dataCol = (spectrogramColumn - MATRIX_WIDTH + x + MATRIX_WIDTH) % MATRIX_WIDTH;
      uint8_t intensity = spectrogramData[dataCol][MATRIX_HEIGHT - 1 - y]; // Flip Y for bottom-to-top display

      // Color mapping: black (silence) -> very dim blue -> blue -> green -> yellow -> red (high)
      uint8_t r = 0, g = 0, b = 0;
      if (intensity < 20)
      {
        // Very low values = completely dark
        r = g = b = 0;
      }
      else if (intensity < 50)
      {
        // Low values = very dim blue (barely visible)
        b = (intensity - 20) / 2;  // Max 15 out of 255 = very dim
        g = 0;
        r = 0;
      }
      else if (intensity < 100)
      {
        // Medium-low = dim to bright blue
        b = 15 + (intensity - 50) * 4;  // From 15 to 215
        g = 0;
        r = 0;
      }
      else if (intensity < 150)
      {
        // Medium = blue to green transition
        b = 215 - (intensity - 100) * 4;
        g = (intensity - 100) * 5;
        r = 0;
      }
      else if (intensity < 200)
      {
        // Medium-high = green to yellow
        g = 255;
        r = (intensity - 150) * 5;
        b = 0;
      }
      else
      {
        // High = yellow to red
        r = 255;
        g = 255 - (intensity - 200) * 4;
        b = 0;
      }

      strip.setPixelColor(getLEDIndex(x, y), strip.Color(r, g, b));
    }
  }

  strip.show();
}

// Test pattern: vertical line on left column
void drawVerticalLine()
{
  strip.clear();
  for (int y = 0; y < MATRIX_HEIGHT; y++)
  {
    // Draw only on x=0 (leftmost column)
    strip.setPixelColor(getLEDIndex(0, y), strip.Color(255, 255, 255)); // White line
  }
  strip.show();
}

// Audio levels histogram with logarithmic frequency bins
void updateAndDrawAudioLevels()
{
  readAudioData();
  
  // Apply window function
  FFT.windowing(FFT_WIN_TYP_HAMMING, FFT_FORWARD);
  
  // Compute FFT
  FFT.compute(FFT_FORWARD);
  
  // Compute magnitudes
  FFT.complexToMagnitude();
  
  // Logarithmic frequency bins from 30Hz to 10kHz
  // 10 bins for 10 columns on the display
  const float minFreq = 30.0;    // 30 Hz
  const float maxFreq = 10000.0; // 10 kHz
  const float logMin = log10(minFreq);
  const float logMax = log10(maxFreq);
  const float logStep = (logMax - logMin) / MATRIX_WIDTH;
  
  // Calculate bin edges in Hz
  float binEdges[MATRIX_WIDTH + 1];
  for (int i = 0; i <= MATRIX_WIDTH; i++) {
    binEdges[i] = pow(10, logMin + i * logStep);
  }
  
  // Convert frequencies to FFT bin indices
  const float binWidth = (float)SAMPLING_FREQUENCY / SAMPLES;
  
  // Clear the display
  strip.clear();
  
  // For each column (frequency bin)
  for (int col = 0; col < MATRIX_WIDTH; col++) {
    // Find FFT bins that fall within this frequency range
    int startBin = (int)(binEdges[col] / binWidth);
    int endBin = (int)(binEdges[col + 1] / binWidth);
    
    // Ensure bins are within valid range
    startBin = max(1, min(startBin, SAMPLES/2 - 1));
    endBin = max(startBin + 1, min(endBin, SAMPLES/2));
    
    // Find peak magnitude in this frequency range
    double peakMag = 0;
    for (int bin = startBin; bin < endBin; bin++) {
      if (vReal[bin] > peakMag) {
        peakMag = vReal[bin];
      }
    }
    
    // Convert to dB scale and normalize
    double dB = 20.0 * log10(peakMag + 1);
    int level = (int)(dB * 2.5); // Scale factor to fit display
    level = constrain(level, 0, 255);
    
    // Map to display height (0-9)
    int barHeight = map(level, 0, 255, 0, MATRIX_HEIGHT);
    
    // Draw the bar for this frequency
    for (int row = 0; row < barHeight; row++) {
      // Draw from bottom up
      int y = MATRIX_HEIGHT - 1 - row;
      
      // Color gradient: green at bottom, yellow in middle, red at top
      uint8_t r, g, b;
      if (row < MATRIX_HEIGHT / 3) {
        // Green
        r = 0;
        g = 255;
        b = 0;
      } else if (row < 2 * MATRIX_HEIGHT / 3) {
        // Yellow
        r = 255;
        g = 255;
        b = 0;
      } else {
        // Red
        r = 255;
        g = 0;
        b = 0;
      }
      
      strip.setPixelColor(getLEDIndex(col, y), strip.Color(r, g, b));
    }
  }
  
  strip.show();
  
  // Debug output every 500ms
  static unsigned long lastDebugLevels = 0;
  if (millis() - lastDebugLevels > 500) {
    Serial.print("Audio Levels - Freq bins (Hz): ");
    for (int i = 0; i < MATRIX_WIDTH; i++) {
      Serial.print((int)binEdges[i]);
      Serial.print("-");
      Serial.print((int)binEdges[i+1]);
      Serial.print(" ");
    }
    Serial.println();
    lastDebugLevels = millis();
  }
}

// Beat detection using bass frequencies
void detectBeat() {
  // Read audio and compute FFT
  readAudioData();
  FFT.windowing(FFT_WIN_TYP_HAMMING, FFT_FORWARD);
  FFT.compute(FFT_FORWARD);
  FFT.complexToMagnitude();
  
  // Calculate bass energy (20Hz - 200Hz range)
  float currentBassEnergy = 0;
  int bassStartBin = (int)(20.0 * SAMPLES / SAMPLING_FREQUENCY);
  int bassEndBin = (int)(200.0 * SAMPLES / SAMPLING_FREQUENCY);
  
  for (int bin = bassStartBin; bin < bassEndBin && bin < SAMPLES/2; bin++) {
    currentBassEnergy += vReal[bin];
  }
  
  // Calculate average bass energy from history
  float averageBassEnergy = 0;
  for (int i = 0; i < 20; i++) {
    averageBassEnergy += bassEnergyHistory[i];
  }
  averageBassEnergy /= 20.0;
  
  // Detect beat if current energy exceeds threshold * average
  unsigned long currentTime = millis();
  if (currentBassEnergy > averageBassEnergy * beatThreshold && 
      currentTime - lastBeatTime > beatCooldown &&
      averageBassEnergy > 10) { // Minimum energy threshold to avoid noise
    beatDetected = true;
    lastBeatTime = currentTime;
    beatBrightness = 255; // Full brightness on beat
    Serial.println("BEAT!");
  }
  
  // Update history
  bassEnergyHistory[bassHistoryIndex] = currentBassEnergy;
  bassHistoryIndex = (bassHistoryIndex + 1) % 20;
  
  // Decay brightness
  if (beatBrightness > 0) {
    beatBrightness = beatBrightness * 0.85; // Fast decay
    if (beatBrightness < 10) beatBrightness = 0;
  }
}

// Display function for beat flash mode
void drawBeatFlash() {
  strip.clear();
  
  if (beatBrightness > 0) {
    // Flash entire matrix with current brightness
    uint8_t r = beatBrightness;
    uint8_t g = beatBrightness / 2;
    uint8_t b = beatBrightness / 4;
    
    for (int x = 0; x < MATRIX_WIDTH; x++) {
      for (int y = 0; y < MATRIX_HEIGHT; y++) {
        strip.setPixelColor(getLEDIndex(x, y), strip.Color(r, g, b));
      }
    }
  }
  
  strip.show();
}

void setup()
{
  Serial.begin(115200);
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  strip.begin();
  strip.setBrightness(50);
  strip.show();

  Wire.begin(SDA_PIN, SCL_PIN);

  // I2C Scanner
  Serial.println("Scanning I2C bus...");
  for (byte addr = 1; addr < 127; addr++)
  {
    Wire.beginTransmission(addr);
    byte error = Wire.endTransmission();
    if (error == 0)
    {
      Serial.print("Device found at address 0x");
      if (addr < 16)
        Serial.print("0");
      Serial.println(addr, HEX);
    }
  }
  Serial.println("I2C scan complete.");

  if (!lsm.begin_I2C())
  {
    Serial.println("Failed to find LSM6DS3 at default address, trying 0x6B...");
    if (!lsm.begin_I2C(0x6B))
    {
      Serial.println("Failed to find LSM6DS3 chip at 0x6B");
    }
    else
    {
      Serial.println("LSM6DS3 found at 0x6B");
    }
  }
  else
  {
    Serial.println("LSM6DS3 found at default address");
  }

  lsm.setAccelRange(LSM6DS_ACCEL_RANGE_4_G);
  lsm.setAccelDataRate(LSM6DS_RATE_104_HZ);
}

void loop()
{
  // Button reading with debounce
  int reading = digitalRead(BUTTON_PIN);
  if (reading != lastButtonState)
  {
    lastDebounceTime = millis();
  }
  if ((millis() - lastDebounceTime) > debounceDelay)
  {
    if (reading != buttonState)
    {
      buttonState = reading;
      if (buttonState == LOW)
      {
        currentMode = (currentMode + 1) % 12; // Now we have 12 modes
        strip.clear();
        strip.show();
        if (currentMode == MODE_LIFE)
        {
          initLife();
          drawLife();
        }
        else if (currentMode == MODE_SWEEP)
        {
          currentSweepIndex = 0;
          drawSweep();
        }
        else if (currentMode == MODE_CENTER)
        {
          drawCenter();
        }
        else if (currentMode == MODE_MULTI_BALL)
        {
          initMultiBalls();
          drawMultiBalls();
        }
        else if (currentMode == MODE_LEVEL)
        {
          // No init needed
        }
        else if (currentMode == MODE_NYAN)
        {
          nyanFrame = 0;
          drawNyan();
        }
        else if (currentMode == MODE_SPECTROGRAM)
        {
          Serial.println("Entering Spectrogram mode...");
          configureI2S();
          // Clear spectrogram data
          memset(spectrogramData, 0, sizeof(spectrogramData));
          spectrogramColumn = 0;
        }
        else if (currentMode == MODE_VERTICAL_LINE)
        {
          Serial.println("Entering Vertical Line test mode...");
          drawVerticalLine();
        }
        else if (currentMode == MODE_AUDIO_LEVELS)
        {
          Serial.println("Entering Audio Levels mode...");
          configureI2S();
        }
        else if (currentMode == MODE_BEAT_FLASH)
        {
          Serial.println("Entering Beat Flash mode...");
          configureI2S();
          // Reset beat detection variables
          beatBrightness = 0;
          for (int i = 0; i < 20; i++) {
            bassEnergyHistory[i] = 0;
          }
          bassHistoryIndex = 0;
        }
      }
    }
  }
  lastButtonState = reading;

  // Read accelerometer
  sensors_event_t accel;
  sensors_event_t gyro;
  sensors_event_t temp;
  lsm.getEvent(&accel, &gyro, &temp);

  if (currentMode == MODE_BALL)
  {
    filter.begin(104); // Match LSM6DS_RATE_104_HZ
  }

  switch (currentMode)
  {
  case MODE_RAINBOW:
    rainbowDissolve();
    delay(50);
    break;
  case MODE_BALL:
    updateBall(accel, gyro);
    drawBall();
    delay(5);
    break;
  case MODE_LIFE:
    if (millis() - lastLifeUpdate > lifeUpdateInterval)
    {
      updateLife();
      drawLife();
      lastLifeUpdate = millis();
    }
    break;
  case MODE_SWEEP:
    if (millis() - lastSweepUpdate > sweepInterval)
    {
      currentSweepIndex = (currentSweepIndex + 1) % NUM_LEDS;
      drawSweep();
      lastSweepUpdate = millis();
    }
    break;
  case MODE_CENTER:
    // Static, no update needed
    break;
  case MODE_MULTI_BALL:
    updateMultiBalls();
    drawMultiBalls();
    delay(50);
    break;
  case MODE_LEVEL:
  {
    // Compute normalized tilt from accel
    float ax = accel.acceleration.x / 9.81;
    float ay = accel.acceleration.y / 9.81;
    float az = accel.acceleration.z / 9.81;
    float magnitude = sqrt(ax * ax + ay * ay + az * az);
    if (magnitude > 0)
    {
      ax /= magnitude;
      ay /= magnitude;
    }
    drawLevel(ax, ay);
    delay(20);
  }
  break;
  case MODE_NYAN:
    if (millis() - lastNyanUpdate > nyanInterval)
    {
      nyanFrame = (nyanFrame + 1) % 4;
      drawNyan();
      lastNyanUpdate = millis();
    }
    break;
  case MODE_SPECTROGRAM:
    if (millis() - lastSpectrogramUpdate > spectrogramInterval)
    {
      updateSpectrogram();
      drawSpectrogram();
      lastSpectrogramUpdate = millis();
    }
    break;
  case MODE_VERTICAL_LINE:
    // Static display, no update needed
    break;
  case MODE_AUDIO_LEVELS:
    updateAndDrawAudioLevels();
    delay(50); // Update rate for audio levels
    break;
  case MODE_BEAT_FLASH:
    detectBeat();
    drawBeatFlash();
    delay(20); // Fast update for responsive beat detection
    break;
  }
}