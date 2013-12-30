#include <Bounce.h>


#include <SPI.h> // Include the Arduino SPI library
#include <Bridge.h>
#include <Console.h>

bool debug = true;
bool isBusMode = false;

const int vm1Pin = 3;
const int vm0RedPin = A1;
const int vm0YellowPin = A2;
const int vm0GreenPin = A0;

const int vm0Pin = 6;
const int vm1RedPin = A3;
const int vm1YellowPin = A4;
const int vm1GreenPin = A5;

Bounce modeToggleDebouncer = Bounce();
const int modeTogglePin = 5;
const int modeCarLedPin = 12;
const int modeBusLedPin = 13;

/* 7-SEGMENT LEDS */
const int ssPin = 8;
const int ss2Pin = 7;

const int rLed1Pin = 2;

int startTime = millis();




// the setup routine runs once when you press reset:
void setup() {
  Bridge.begin();
  Console.begin();
  
  pinMode(vm0Pin, OUTPUT);
  pinMode(vm0RedPin, OUTPUT);
  pinMode(vm0YellowPin, OUTPUT);
  pinMode(vm0GreenPin, OUTPUT);

  pinMode(vm1Pin, OUTPUT);
  pinMode(vm1RedPin, OUTPUT);
  pinMode(vm1YellowPin, OUTPUT);
  pinMode(vm1GreenPin, OUTPUT);
  
  pinMode(modeTogglePin, INPUT);
  pinMode(modeCarLedPin, OUTPUT);
  pinMode(modeBusLedPin, OUTPUT);
  
  digitalWrite(modeTogglePin, HIGH);
  digitalWrite(modeCarLedPin, !isBusMode);
  digitalWrite(modeBusLedPin, isBusMode);

  modeToggleDebouncer.attach(modeTogglePin);
  modeToggleDebouncer.interval(5);
    
  pinMode(ssPin, OUTPUT);  // Set the SS pin as an output
  pinMode(ss2Pin, OUTPUT);

  digitalWrite(ssPin, HIGH);  // Set the SS pin HIGH
  digitalWrite(ss2Pin, HIGH);
  
  SPI.begin();  // Begin SPI hardware
  SPI.setClockDivider(SPI_CLOCK_DIV64);  // Slow down SPI clock
  // --------
  
  // Clear the display, and then turn on all segments and decimals
  clearDisplaySPI(ssPin);  // Clears display, resets cursor
  clearDisplaySPI(ss2Pin);  // Clears display, resets cursor
  
  // Custom function to send four bytes via SPI
  //  The SPI.transfer function only allows sending of a single
  //  byte at a time.
//  setDecimalsSPI(0b111111);  // Turn on all decimals, colon, apos
  
  // Flash brightness values at the beginning
//  setBrightnessSPI(255);  // High brightness
  
  // Clear the display before jumping into loop
  clearDisplaySPI(ssPin);  
  clearDisplaySPI(ss2Pin);
}

// the loop routine runs over and over again forever:
void loop() {
//  processDebug();
  
  doModeToggleButton();
  
  do7SegDisplays();

  doMinutes();  
//  digitalWrite(vm1GreenPin, HIGH);

  delay(10);
}

void doModeToggleButton() {
  Console.print("Toggle:");
  Console.println(digitalRead(5));

  if (modeToggleDebouncer.update()) {
    int value = modeToggleDebouncer.read();
    
    Console.println(value);
    if (value == HIGH) {
      isBusMode = !isBusMode;
      
      digitalWrite(modeBusLedPin, isBusMode);
      digitalWrite(modeCarLedPin, !isBusMode);
    }
  }
}

void doMinutes() {
  int vmMinutes0 = 0;
  int vmMinutes1 = 0;
  
  vmMinutes0 = getMinutes(0);
  vmMinutes1 = getMinutes(1);

  updateMinutes(vm0Pin, vmMinutes0);
  updateMinutes(vm1Pin, vmMinutes1);
}

void do7SegDisplays() {
  char disp1Val[4];
  char disp2Val[4];
  
  if (isBusMode) {
    Bridge.get((char*)"BUS_0_CODE", disp1Val, 4);
    Bridge.get((char*)"BUS_1_CODE", disp2Val, 4); 
  } else {
    Bridge.get((char*)"CAR_0_CODE", disp1Val, 4);
    Bridge.get((char*)"CAR_1_CODE", disp2Val, 4); 
  }

//  Console.println("7SEG:");
//  Console.println(disp1Val);
//  Console.println(disp2Val);
//  Console.println("---------");
  
  s7sSendStringSPI(disp1Val, ssPin);
  s7sSendStringSPI(disp2Val, ss2Pin);
}

int getMinutes(int pos) {
 
  char minutes[3];
  char keyBuf[11];
  String key;
  int idx = 0;
  
  if (isBusMode) {
    key = "BUS_";
  } else {
    key = "CAR_";
  }
  
  key = key + String(pos) + "_MINS";
  
  key.toCharArray(keyBuf, 11);
  
  idx = Bridge.get(keyBuf, minutes, 2);
  
  minutes[idx] = 0;
  
//  Console.println("----- minutes ----");
//  Console.println(keyBuf);
//  Console.println(idx);
//  Console.println(minutes);
//  Console.println(atoi(minutes));
//  Console.println("-----");
  
  return atoi(minutes);  
}

int convertMinutesToVMByte(int minutes) {
  return 255 * (minutes / 60.0);
}

void updateMinutes(int vmPin, int minutes) {
  int redPin;
  int greenPin;
  int yellowPin;
  
  if (vmPin == vm0Pin) {
    redPin = vm0RedPin;
    yellowPin = vm0YellowPin;
    greenPin = vm0GreenPin;
  } else {
    redPin = vm1RedPin;
    yellowPin = vm1YellowPin;
    greenPin = vm1GreenPin;
  }
    
  if ((!isBusMode && minutes < 35) || (isBusMode && minutes > 20)) { //green on
    digitalWrite(greenPin, HIGH);
    digitalWrite(yellowPin, LOW);
    digitalWrite(redPin, LOW);
  } else if ((!isBusMode && minutes >= 35 && minutes < 45) || (isBusMode && minutes < 20 && minutes >= 10)) {
    digitalWrite(greenPin, LOW);
    digitalWrite(yellowPin, HIGH);
    digitalWrite(redPin, LOW);
  } else {
    digitalWrite(greenPin, LOW);
    digitalWrite(yellowPin, LOW);
    digitalWrite(redPin, HIGH);
  }
  
  analogWrite(vmPin, convertMinutesToVMByte(minutes));
}

/* 7-SEGMENT FUNCTIONS */
// This custom function works somewhat like a serial.print.
//  You can send it an array of chars (string) and it'll print
//  all of the characters in the array.
void s7sSendStringSPI(String toSend, int ssPin)
{
  digitalWrite(ssPin, LOW);
  for (int i=0; i<4; i++)
  {
    SPI.transfer(toSend[i]);
  }
  digitalWrite(ssPin, HIGH);
}

// Send the clear display command (0x76)
//  This will clear the display and reset the cursor
void clearDisplaySPI(int ssPin)
{
  digitalWrite(ssPin, LOW);
  SPI.transfer(0x76);  // Clear display command
  digitalWrite(ssPin, HIGH);
}

// Set the displays brightness. Should receive byte with the value
//  to set the brightness to
//  dimmest------------->brightest
//     0--------127--------255
void setBrightnessSPI(byte value, int ssPin)
{
  digitalWrite(ssPin, LOW);
  SPI.transfer(0x7A);  // Set brightness command byte
  SPI.transfer(value);  // brightness data byte
  digitalWrite(ssPin, HIGH);
}

// Turn on any, none, or all of the decimals.
//  The six lowest bits in the decimals parameter sets a decimal 
//  (or colon, or apostrophe) on or off. A 1 indicates on, 0 off.
//  [MSB] (X)(X)(Apos)(Colon)(Digit 4)(Digit 3)(Digit2)(Digit1)
void setDecimalsSPI(byte decimals, int ssPin)
{
  digitalWrite(ssPin, LOW);
  SPI.transfer(0x77);
  SPI.transfer(decimals);
  digitalWrite(ssPin, HIGH);
}

