#include "motor_control.h"
#include "config.h"
#include <Arduino.h>

// Usa canais LEDC 4..7 (timers 2 e 3) para não conflitar com LEDC_CHANNEL_0 / TIMER_0 da câmera OV2640.
static constexpr uint8_t PWM_CH_LEFT_A = 4;
static constexpr uint8_t PWM_CH_LEFT_B = 5;
static constexpr uint8_t PWM_CH_RIGHT_A = 6;
static constexpr uint8_t PWM_CH_RIGHT_B = 7;

static bool g_motorsActive = false;

static void pwmAttach(uint8_t pin, uint8_t channel) {
#if defined(ESP_ARDUINO_VERSION_MAJOR) && (ESP_ARDUINO_VERSION_MAJOR >= 3)
  ledcAttachChannel(pin, MOTOR_PWM_FREQ_HZ, MOTOR_PWM_RES_BITS, channel);
#else
  ledcSetup(channel, MOTOR_PWM_FREQ_HZ, MOTOR_PWM_RES_BITS);
  ledcAttachPin(pin, channel);
#endif
}

static void pwmSetDuty(uint8_t pin, uint8_t channel, uint32_t duty) {
#if defined(ESP_ARDUINO_VERSION_MAJOR) && (ESP_ARDUINO_VERSION_MAJOR >= 3)
  (void)channel;
  ledcWrite(pin, duty);
#else
  (void)pin;
  ledcWrite(channel, duty);
#endif
}

static int clampPwm(int value) {
  if (value > 255) return 255;
  if (value < -255) return -255;
  return value;
}

void motorInit() {
#if MOTOR_DRIVER_6PIN
  pinMode(MOTOR_LEFT_IN1_PIN, OUTPUT);
  pinMode(MOTOR_LEFT_IN2_PIN, OUTPUT);
  pinMode(MOTOR_RIGHT_IN3_PIN, OUTPUT);
  pinMode(MOTOR_RIGHT_IN4_PIN, OUTPUT);

  digitalWrite(MOTOR_LEFT_IN1_PIN, LOW);
  digitalWrite(MOTOR_LEFT_IN2_PIN, LOW);
  digitalWrite(MOTOR_RIGHT_IN3_PIN, LOW);
  digitalWrite(MOTOR_RIGHT_IN4_PIN, LOW);

  pwmAttach(MOTOR_LEFT_PWM_PIN, PWM_CH_LEFT_A);
  pwmAttach(MOTOR_RIGHT_PWM_PIN, PWM_CH_RIGHT_A);
#else
  pwmAttach(MOTOR_LEFT_IN1_PIN, PWM_CH_LEFT_A);
  pwmAttach(MOTOR_LEFT_IN2_PIN, PWM_CH_LEFT_B);
  pwmAttach(MOTOR_RIGHT_IN3_PIN, PWM_CH_RIGHT_A);
  pwmAttach(MOTOR_RIGHT_IN4_PIN, PWM_CH_RIGHT_B);
#endif

  motorStop();
}

static void driveSingleSide(
    int speed,
    bool invert,
    uint8_t pwmPin,
    uint8_t inAPin,
    uint8_t inBPin,
    uint8_t chA,
    uint8_t chB
) {
  int clamped = clampPwm(speed);
  if (invert) {
    clamped = -clamped;
  }

#if MOTOR_DRIVER_6PIN
  (void)chB;
  if (clamped > 0) {
    digitalWrite(inAPin, HIGH);
    digitalWrite(inBPin, LOW);
    pwmSetDuty(pwmPin, chA, static_cast<uint32_t>(clamped));
  } else if (clamped < 0) {
    digitalWrite(inAPin, LOW);
    digitalWrite(inBPin, HIGH);
    pwmSetDuty(pwmPin, chA, static_cast<uint32_t>(-clamped));
  } else {
    digitalWrite(inAPin, LOW);
    digitalWrite(inBPin, LOW);
    pwmSetDuty(pwmPin, chA, 0);
  }
#else
  (void)pwmPin;
  if (clamped > 0) {
    pwmSetDuty(inAPin, chA, static_cast<uint32_t>(clamped));
    pwmSetDuty(inBPin, chB, 0);
  } else if (clamped < 0) {
    pwmSetDuty(inAPin, chA, 0);
    pwmSetDuty(inBPin, chB, static_cast<uint32_t>(-clamped));
  } else {
    pwmSetDuty(inAPin, chA, 0);
    pwmSetDuty(inBPin, chB, 0);
  }
#endif
}

void motorSetSpeeds(int left, int right) {
  int safeLeft = clampPwm(left);
  int safeRight = clampPwm(right);

  driveSingleSide(
      safeLeft,
      INVERT_LEFT_MOTOR,
      MOTOR_LEFT_PWM_PIN,
      MOTOR_LEFT_IN1_PIN,
      MOTOR_LEFT_IN2_PIN,
      PWM_CH_LEFT_A,
      PWM_CH_LEFT_B
  );

  driveSingleSide(
      safeRight,
      INVERT_RIGHT_MOTOR,
      MOTOR_RIGHT_PWM_PIN,
      MOTOR_RIGHT_IN3_PIN,
      MOTOR_RIGHT_IN4_PIN,
      PWM_CH_RIGHT_A,
      PWM_CH_RIGHT_B
  );

  g_motorsActive = (safeLeft != 0 || safeRight != 0);
}

void motorStop() {
  motorSetSpeeds(0, 0);
}

bool motorIsActive() {
  return g_motorsActive;
}
