#ifndef _R4_API_FLASH_H
#define _R4_API_FLASH_H

// External Flash definitions
#define EF_IMAGE_BASE		    0x01000000
#define EF_IMAGE_END		    0x0100EFFF
#define EF_USER_BASE		    0x0100F100
#define EF_USER_END			    0x0100FFFF

#define EF_PAGE_SIZE		    2048    // Bytes
#define EF_PAGES_PER_BLOCK	    64

#define IF_PAGE_SIZE            256     // Bytes
#define IF_PAGES_PER_BLOCK      1

#define SXGA_BP_SIZE			0x28000	// (1280 x 1024 / 8) bytes

#define SXGA_PAGES_PER_BP		80
#define WXGA_PAGES_PER_BP		64

// Base page of Repertoire in internal Flash
#define IF_REP_BASE_R4			0x0200  // R4
#define IF_REP_BASE_R12         0x0180  // R12

#ifdef __cplusplus
extern "C" {
#endif

FDD_RESULT R4_FlashRead(void *, uint16_t, uint16_t);
FDD_RESULT R4_FlashWrite(const void *, uint16_t, uint16_t);
FDD_RESULT R4_FlashBurn(uint32_t);
FDD_RESULT R4_FlashGrab(uint32_t);

#ifdef __cplusplus
}
#endif

#endif // _R4_API_FLASH_H
