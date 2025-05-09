## This repo demonstrates python code to power toggle the Ayre v-1x using Global Cache [iTACH](https://www.amazon.com/stores/page/87D23D98-A025-47EE-AAAF-FE41280B7371?ingress=2&visitId=5ce6c02b-6105-46b7-8996-f6ff75a32544&store_ref=bl_ast_dp_brandLogo_sto&ref_=ast_bln)
* use case is
*   The V-1x does not have a 12v controller signal input/output so in order to slave it to other devices code is needed
*   This repo contains images related to orientation of the IR transmitters provided in box by iTach Global Cache
## Raw codes:
function, code1, hexcode1, code2, hexcode2

"POWER TOGGLE","sendir,1:1,1,36000,1,1,32,32,64,64,64,32,32,32,32,32,32,32,32,32,32,64,32,32,64,32,32,2487",
"0000 0073 000B 0000 0020 0020 0040 0040 0040 0020 0020 0020 0020 0020 0020 0020 0020 0020 0020 0040 0020 0020 0040 0020 0020 09B7","sendir,1:1,1,36000,1,1,32,32,32,32,32,32,64,32,32,32,32,32,32,32,32,32,32,64,32,32,64,32,32,2487",
"0000 0073 000C 0000 0020 0020 0020 0020 0020 0020 0040 0020 0020 0020 0020 0020 0020 0020 0020 0020 0020 0040 0020 0020 0040 0020 0020 09B7"

# A note about iTACH ports
* Ports are not numbered in hardware. No documentation is provided of port numbers
* Port 1 - **farthest from Ethernet RJ46**
* Port 3 - used for IR  blaster **adjacent to RJ45**
* IR transmitter signal [path](https://github.com/smichalove/iTACH_AYRE/blob/main/itach%20IR.png)
* Blaster signal [path](https://github.com/smichalove/iTACH_AYRE/blob/main/itach%20IR.png)
## Amazon Store
https://www.amazon.com/stores/Global+Cach%C3%A9/page/9B16D5C3-4BA1-4A4E-8331-C4AF232F1FD6?lp_asin=B003BFTKUC&ref_=ast_bln&store_ref=bl_ast_dp_brandLogo_sto
