# Project Requirements – Vehicle Gate License Plate Detection System

## 1. Functional Requirements

- [ ] The system must detect if a vehicle approaching the gate is a **truck/lorry** or **other vehicle**.
- [ ] The system must extract and recognize the **license plate** of the detected vehicle.
- [ ] The license plate must be **compared against a list of pre-registered plates** stored in a local database.
- [ ] If the detected vehicle is a **truck** and its license plate is **in the database**, the system must **trigger Arduino to open the gate**.
- [ ] If the detected vehicle is **not a truck** (e.g., car), the system must **trigger a buzzer via Arduino** as a warning.
- [ ] The user interface must provide a **live video stream** showing the camera feed.
- [ ] The interface must show:
  - [ ] “Truck detected” message when a truck is recognized.
  - [ ] “Vehicle authorized – gate opening” if the plate is in the database.
- [ ] The interface must include a **separate page for license plate registration** and management.

## 2. Technical Requirements

- [ ] The application must be built using **Flask** (Python backend).
- [ ] The system must support being run either:
  - [ ] As a **mobile-accessible web application**, or
  - [ ] On a **PC** with the **mobile phone camera used as a webcam**.
- [ ] The object detection model must support **vehicle and license plate recognition** (e.g., YOLOv8).
- [ ] The system must use **serial communication** to control an **Arduino** for gate and buzzer actions.

## 3. Dataset Requirements

- [ ] The dataset must contain:
  - [ ] **1,000 labeled images of trucks**
  - [ ] **1,000 labeled images of other vehicles**
- [ ] Each image must be annotated with bounding boxes for:
  - [ ] The **vehicle**
  - [ ] The **license plate**
- [ ] The dataset must be delivered as a **ZIP file via Google Drive**.
- [ ] The dataset must be compatible with YOLOv8 format.

## 4. Deployment and Version Control

- [ ] All source code must be uploaded to a **public GitHub repository**.
- [ ] The dataset link (ZIP from Google Drive) must be included in the README.
