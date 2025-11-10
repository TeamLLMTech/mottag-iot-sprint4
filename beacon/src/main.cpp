#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#define DEVICE_NAME         "ESP32"
#define SERVICE_UUID        "7A0247E7-8E88-409B-A959-AB5092DDB03E"
#define CHARACTERISTIC_UUID "82258BAA-DF72-47E8-99BC-B73D7ECD08A5"

BLEServer *pServer;
BLECharacteristic *pCharacteristic;
bool deviceConnected = false;

int buzzer1 = 25;
int buzzer2 = 26;
int ledPin = 18;

bool shouldMakeAnnouncement = false;

void playTone(int frequency, int duration) {
  if (frequency > 0) {
    ledcWriteTone(0, frequency);
    ledcWrite(0, 255);
  } else {
    ledcWriteTone(0, 0);
  }
  delay(duration);
  ledcWriteTone(0, 0);
}

void playAnnounceTone() {
  int melody[] = { 1000, 1200, 1500, 1800, 2000 };
  int noteDurations[] = { 200, 200, 200, 200, 400 };

  for (int i = 0; i < 5; i++) {
    playTone(melody[i], noteDurations[i]);
    delay(50);
  }
}

void makeAnnouncement() {
  digitalWrite(ledPin, HIGH);
  playAnnounceTone();
  digitalWrite(ledPin, LOW);
  delay(1000);
}

class MyServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer *pServer) {
    deviceConnected = true;
    Serial.println("deviceConnected = true");
  };

  void onDisconnect(BLEServer *pServer) {
    deviceConnected = false;
    Serial.println("deviceConnected = false");
    pServer->startAdvertising();
    Serial.println("Advertising restarted");
  }
};

class MyCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *pCharacteristic) {
    String rxValue = String(pCharacteristic->getValue().c_str());

    if (rxValue.length() > 0) {
      Serial.println("*********");
      Serial.print("Received Value: ");
      for (int i = 0; i < rxValue.length(); i++) {
        Serial.print(rxValue[i]);
      }
      Serial.println();
      Serial.println("*********");

      shouldMakeAnnouncement = !shouldMakeAnnouncement;
    }
  }
};

void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.println("Initializing...");
  Serial.flush();

  BLEDevice::init(DEVICE_NAME);
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  // Create the BLE Service
  BLEService *pService = pServer->createService(BLEUUID(SERVICE_UUID));

  // Create a BLE Characteristic
  pCharacteristic = pService->createCharacteristic(
    CHARACTERISTIC_UUID, BLECharacteristic::PROPERTY_WRITE
  );
  pCharacteristic->setCallbacks(new MyCallbacks());
  pCharacteristic->addDescriptor(new BLE2902());

  // Start the service
  pService->start();

  // Start advertising
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(true);
  pAdvertising->start();

  pinMode(ledPin, OUTPUT);
  ledcSetup(0, 2000, 8);
  ledcAttachPin(buzzer1, 0);
  ledcAttachPin(buzzer2, 0);

  Serial.println("BLE Service defined and advertising!");
}

void loop() {
  if (shouldMakeAnnouncement) {
    makeAnnouncement();
  }
}