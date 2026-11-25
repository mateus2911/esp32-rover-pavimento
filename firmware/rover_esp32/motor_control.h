#ifndef ROVER_MOTOR_CONTROL_H
#define ROVER_MOTOR_CONTROL_H

#include <stdint.h>

void motorInit();
void motorSetSpeeds(int left, int right);
void motorStop();
bool motorIsActive();

#endif // ROVER_MOTOR_CONTROL_H
