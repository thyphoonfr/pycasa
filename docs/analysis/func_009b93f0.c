// Address: 009b93f0
// Function: FUN_009b93f0
// Target requested: 0x009b93f0

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 FUN_009b93f0(void)

{
  float fVar1;
  float fVar2;
  uint *in_EAX;
  uint uVar3;
  uint uVar4;
  uint unaff_ESI;
  uint unaff_EDI;
  
  uVar4 = *in_EAX;
  if ((((uVar4 != 0) || (in_EAX[2] != 0)) || (in_EAX[1] != 0)) || (in_EAX[3] != 0)) {
    fVar1 = (float)(int)unaff_ESI;
    if ((int)unaff_ESI < 0) {
      fVar1 = fVar1 + _DAT_00cf39e4;
    }
    fVar1 = fVar1 / (float)_DAT_00cf3b78;
    fVar2 = (float)(int)unaff_EDI;
    if ((int)unaff_EDI < 0) {
      fVar2 = fVar2 + _DAT_00cf39e4;
    }
    fVar2 = fVar2 / (float)_DAT_00cf3b78;
    uVar3 = in_EAX[2];
    if ((int)uVar3 < (int)uVar4) {
      in_EAX[2] = uVar4;
      *in_EAX = uVar3;
    }
    uVar4 = in_EAX[3];
    if ((int)uVar4 < (int)in_EAX[1]) {
      in_EAX[3] = in_EAX[1];
      in_EAX[1] = uVar4;
    }
    uVar4 = (uint)ROUND((float)(int)*in_EAX * fVar1);
    if ((int)uVar4 < 0) {
      uVar3 = 0;
    }
    else {
      uVar3 = unaff_ESI - 1;
      if (uVar4 <= unaff_ESI - 1) {
        uVar3 = uVar4;
      }
    }
    *in_EAX = uVar3;
    uVar4 = (uint)ROUND((float)(int)in_EAX[2] * fVar1);
    if ((int)uVar4 < 1) {
      uVar4 = 1;
    }
    else if (unaff_ESI < uVar4) {
      uVar4 = unaff_ESI;
    }
    in_EAX[2] = uVar4;
    uVar4 = (uint)ROUND((float)(int)in_EAX[1] * fVar2);
    if ((int)uVar4 < 0) {
      uVar3 = 0;
    }
    else {
      uVar3 = unaff_EDI - 1;
      if (uVar4 <= unaff_EDI - 1) {
        uVar3 = uVar4;
      }
    }
    in_EAX[1] = uVar3;
    uVar4 = (uint)ROUND((float)(int)in_EAX[3] * fVar2);
    if ((int)uVar4 < 1) {
      uVar4 = 1;
    }
    else if (unaff_EDI < uVar4) {
      uVar4 = unaff_EDI;
    }
    in_EAX[3] = uVar4;
    if ((int)in_EAX[2] <= (int)*in_EAX) {
      *in_EAX = in_EAX[2] - 1;
    }
    if ((int)uVar4 <= (int)in_EAX[1]) {
      in_EAX[1] = uVar4 - 1;
    }
  }
  return 0;
}


