#ifndef _R4_API_DEVICE_H
#define _R4_API_DEVICE_H

#define FDD_VID                 0x19EC                                  // ForthDD USB VendorID

#define R4_HID_PID              0x0301                                  // ForthDD USB ProductID for R4 HID
#define R4_WINUSB_GUID          "54ED7AC9-CC23-4165-BE32-79016BAFB950"  // ForthDD WinUSB GUID for R4 (Required by Windows)
#define R4_WINUSB_PID		0x0403                                  // ForthDD WinUSB PID for R4 (Required by Linux)
#define R4_RS232_BAUDRATE       115200                                  // ForthDD RS-232 Baud rate

#define ATMEL_VID               0x03EB                                  // Atmel USB VendorID
#define ATMEL_SAM_BA_PID        0x6124                                  // Atmel USB ProductID for SAM-BA
#define ATMEL_SAM_BA_BAUDRATE   115200                                  // Atmel SAM-BA Baud rate

#ifdef __cplusplus
extern "C" {
#endif

FDD_RESULT R4_DevGetProgress(uint8_t *);
FDD_RESULT R4_DevEnumerateWinUSB(DevPtr *, uint16_t *);

#ifdef __cplusplus
}
#endif

#endif // _R4_API_DEVICE_H
