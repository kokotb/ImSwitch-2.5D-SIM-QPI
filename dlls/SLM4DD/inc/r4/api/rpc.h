#ifndef _R4_API_RPC_H
#define _R4_API_RPC_H

#ifdef __cplusplus
extern "C" {  
#endif

FDD_RESULT R4_RpcSysGetBoardType(uint8_t *);
FDD_RESULT R4_RpcSysReboot(void);
FDD_RESULT R4_RpcSysGetStoredChecksum(uint16_t, uint32_t *);
FDD_RESULT R4_RpcSysGetCalculatedChecksum(uint16_t, uint32_t *);
FDD_RESULT R4_RpcSysGetBitplaneCount(uint32_t *);
FDD_RESULT R4_RpcSysReloadRepertoire(void);
FDD_RESULT R4_RpcSysGetRepertoireName(char *, uint8_t);
FDD_RESULT R4_RpcSysGetRepertoireUniqueId(char *, uint8_t);
FDD_RESULT R4_RpcSysSaveSettings(void);
FDD_RESULT R4_RpcSysGetDaughterboardType(uint8_t *);
FDD_RESULT R4_RpcSysGetADC(uint8_t, uint16_t *);
FDD_RESULT R4_RpcSysGetBoardID(uint8_t *);
FDD_RESULT R4_RpcSysGetDisplayType(uint8_t *);
FDD_RESULT R4_RpcSysGetDisplayTemp(uint16_t *);
FDD_RESULT R4_RpcSysGetSerialNum(uint32_t *);

FDD_RESULT R4_RpcMicroGetCodeTimestamp(char *, uint8_t);
FDD_RESULT R4_RpcMicroGetCodeVersion(uint16_t *);

FDD_RESULT R4_RpcFlashEraseBlock(uint32_t);

FDD_RESULT R4_RpcFpgaRead(uint8_t, void *, uint8_t);
FDD_RESULT R4_RpcFpgaWrite(uint8_t, const void *, uint8_t);

FDD_RESULT R4_RpcRoGetCount(uint16_t *);
FDD_RESULT R4_RpcRoGetSelected(uint16_t *);
FDD_RESULT R4_RpcRoGetDefault(uint16_t *);
FDD_RESULT R4_RpcRoSetSelected(uint16_t);
FDD_RESULT R4_RpcRoSetDefault(uint16_t);
FDD_RESULT R4_RpcRoGetActivationType(uint8_t *);
FDD_RESULT R4_RpcRoGetActivationState(uint8_t *);
FDD_RESULT R4_RpcRoActivate(void);
FDD_RESULT R4_RpcRoDeactivate(void);
FDD_RESULT R4_RpcRoGetName(uint16_t, char *, uint8_t);

FDD_RESULT R4_RpcLedSet(uint8_t);
FDD_RESULT R4_RpcLedGet(uint8_t *);

FDD_RESULT R4_RpcFlipTpSet(uint8_t);
FDD_RESULT R4_RpcFlipTpGet(uint8_t *);

FDD_RESULT R4_RpcMaintLedSet(BOOL);
FDD_RESULT R4_RpcMaintLedGet(BOOL *);

FDD_RESULT R4_RpcM137CurrentLimitSet(uint8_t);
FDD_RESULT R4_RpcM137CurrentLimitGet(uint8_t *);
FDD_RESULT R4_RpcM137TemperatureLimitSet(uint8_t);
FDD_RESULT R4_RpcM137TemperatureLimitGet(uint8_t *);


#ifdef __cplusplus
}
#endif

#endif // _R4_API_RPC_H
