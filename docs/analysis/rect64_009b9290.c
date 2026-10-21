// Address: 009b9290
// Function: FUN_009b9290
// Target requested: 0x009b9290

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 __fastcall FUN_009b9290(undefined4 param_1,int param_2,int param_3)

{
  float fVar1;
  float fVar2;
  int *in_EAX;
  int iVar3;
  
  if ((((*in_EAX != 0) || (in_EAX[2] != 0)) || (in_EAX[1] != 0)) || (in_EAX[3] != 0)) {
    if ((param_3 == 0) || (param_2 == 0)) {
      return 0xffffffff;
    }
    fVar1 = (float)param_3;
    if (param_3 < 0) {
      fVar1 = fVar1 + _DAT_00cf39e4;
    }
    fVar1 = (float)_DAT_00cf3b78 / fVar1;
    fVar2 = (float)param_2;
    if (param_2 < 0) {
      fVar2 = fVar2 + _DAT_00cf39e4;
    }
    fVar2 = (float)_DAT_00cf3b78 / fVar2;
    iVar3 = (int)ROUND((float)*in_EAX * fVar1);
    if (iVar3 < 0) {
      iVar3 = 0;
    }
    else if (0xfffe < iVar3) {
      iVar3 = 0xfffe;
    }
    *in_EAX = iVar3;
    iVar3 = (int)ROUND((float)in_EAX[2] * fVar1);
    if (iVar3 < 1) {
      iVar3 = 1;
    }
    else if (0xffff < iVar3) {
      iVar3 = 0xffff;
    }
    in_EAX[2] = iVar3;
    iVar3 = (int)ROUND((float)in_EAX[1] * fVar2);
    if (iVar3 < 0) {
      iVar3 = 0;
    }
    else if (0xfffe < iVar3) {
      iVar3 = 0xfffe;
    }
    in_EAX[1] = iVar3;
    iVar3 = (int)ROUND((float)in_EAX[3] * fVar2);
    if (iVar3 < 1) {
      iVar3 = 1;
    }
    else if (0xffff < iVar3) {
      iVar3 = 0xffff;
    }
    in_EAX[3] = iVar3;
    if (in_EAX[2] <= *in_EAX) {
      *in_EAX = in_EAX[2] + -1;
    }
    if (iVar3 <= in_EAX[1]) {
      in_EAX[1] = iVar3 + -1;
    }
  }
  return 0;
}


