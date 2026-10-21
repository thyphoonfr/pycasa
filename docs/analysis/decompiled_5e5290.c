// Address: 005e4ac0
// Function: FUN_005e4ac0
// Target requested: 005e5290

int __thiscall FUN_005e4ac0(int *param_1,undefined4 *param_2)

{
  ushort uVar1;
  short sVar2;
  char cVar3;
  int iVar4;
  undefined4 uVar5;
  uint uVar6;
  uint uVar7;
  undefined4 uVar8;
  uint uStack_28;
  uint uStack_24;
  undefined4 uStack_20;
  undefined4 uStack_1c;
  undefined4 uStack_18;
  undefined4 uStack_14;
  undefined4 uStack_10;
  
  if (param_2[8] != 0) {
    iVar4 = (**(code **)(*param_1 + 0x58))(param_2);
    return iVar4;
  }
  if ((param_1[0xc25] != 0) &&
     ((((iVar4 = param_2[1], iVar4 == 0x1c || (iVar4 == 5)) || (iVar4 == 3)) || (iVar4 == 0x7e)))) {
    func_0x00550fd0(*param_2,param_2[2],param_2[3]);
  }
  iVar4 = param_2[1];
  if ((iVar4 == 0x133) && (param_2[3] == param_1[0x3d2])) {
    uStack_28 = param_1[0x3da];
    uVar5 = param_2[2];
    uVar7 = uStack_28 >> 0x10 & 0xff | (uStack_28 & 0xff) << 0x10 | uStack_28 & 0xff00;
    SetBkColor(uVar5,uVar7);
    SetTextColor(uVar5,0);
    uVar6 = uStack_28;
    if ((param_1[0xce1] != 0) && (param_1[0xce2] != uStack_28)) {
      DeleteObject(param_1[0xce1]);
      param_1[0xce1] = 0;
      iVar4 = CreateSolidBrush(uVar7);
      param_1[0xce1] = iVar4;
      param_1[0xce2] = uVar6;
    }
    return param_1[0xce1];
  }
  if (((iVar4 == 0x135) || (iVar4 == 0x133)) || ((iVar4 == 0x19 || (iVar4 == 0x138)))) {
    iVar4 = func_0x007bd130();
    return iVar4;
  }
  if (iVar4 == 0x212) {
    if (-1 < param_1[0x38c]) {
      func_0x005eb160(param_1[0x38c]);
      param_1[0x38c] = -1;
      return 0;
    }
    if (-1 < param_1[0x38d]) {
      func_0x005eb1e0();
      param_1[0x38d] = -1;
      return 0;
    }
  }
  if (iVar4 != 0x11f) {
    if (iVar4 == 0x116) {
      if (param_1[0xd29] != 0) {
        return 0;
      }
      func_0x0056e0f0(param_2[2]);
      return 0;
    }
    if (iVar4 == 0x112) {
      if (param_2[2] == 0xf020) {
        func_0x00575f50();
      }
      else if (param_2[2] == 0xf060) {
        iVar4 = func_0x0057c4e0();
        return iVar4;
      }
    }
    if (param_2[1] == 0x4ff) {
      if (*(char *)((int)param_1 + 0x332f) != '\0') {
        return 0;
      }
      cVar3 = func_0x0057c430(0xffffffff);
      if (cVar3 != '\0') {
        return 0;
      }
      if (param_1[0x54] != param_1[0x53]) {
        return 0;
      }
      iVar4 = (**(code **)(*param_1 + 0x24))();
      uVar5 = *(undefined4 *)(iVar4 + 0x6c);
      iVar4 = IsIconic(uVar5);
      if (iVar4 == 0) {
        uVar8 = 5;
      }
      else {
        uVar8 = 9;
      }
      ShowWindow(uVar5,uVar8);
      iVar4 = (**(code **)(*param_1 + 0x24))();
      if (*(int *)(iVar4 + 0x6c) != 0) {
        SetForegroundWindow(*(int *)(iVar4 + 0x6c));
      }
      if (param_2[3] != 0x7fffffff) {
        func_0x005fa020(param_1,param_2[3],1,1);
      }
      *(undefined1 *)(param_1 + 0x91) = 1;
    }
    if (param_2[1] == 0x111) {
      iVar4 = param_2[3];
      sVar2 = *(short *)((int)param_2 + 10);
      if (iVar4 == 0) {
        iVar4 = (**(code **)(*param_1 + 0x5c))(param_2);
        return iVar4;
      }
      if (iVar4 == param_1[0x3d2]) {
        if (sVar2 == 0x300) {
          cVar3 = func_0x0097fb90();
          if (cVar3 == '\0') {
            func_0x0065b840(param_1,0,1,1);
          }
        }
        else {
LAB_005e4e34:
          if (sVar2 == 0x400) goto LAB_005e4e3c;
        }
      }
      else {
        if (sVar2 != 0x300) goto LAB_005e4e34;
LAB_005e4e3c:
        uVar5 = GetWindowLongA(iVar4,0xffffffeb);
        iVar4 = func_0x00c07db2(uVar5,0,0xd3ed88,0xd3f894,0);
        if (iVar4 != 0) {
          if (sVar2 == 0x400) {
            func_0x007bccf0();
          }
          else if (sVar2 == 0x300) {
            func_0x007bcda0();
          }
        }
      }
    }
    iVar4 = param_2[1];
    if (iVar4 == 0x319) {
      cVar3 = FUN_00579330();
      if ((cVar3 != '\0') && ((*(ushort *)((int)param_2 + 0xe) & 0xfff) == 1)) {
        cVar3 = func_0x005f2650();
        if (cVar3 != '\0') {
          func_0x009cd8a0();
          return 0xf4241;
        }
        func_0x00566270();
      }
      return 0xf4241;
    }
    if (iVar4 == 0x233) {
      uVar5 = param_2[2];
      uVar6 = GlobalSize(uVar5);
      if (uVar6 < 0x14) {
        return -1;
      }
      func_0x00537330(param_1,uVar5);
      DragFinish(uVar5);
      return 1000000;
    }
    if (iVar4 == 0x3b9) {
      if (param_2[2] == 1) {
        func_0x0075f390(1);
      }
      return 0xf4241;
    }
    if (iVar4 == 0x4a) goto LAB_005e4f3d;
    if (iVar4 < 0x205) {
      if (((iVar4 == 0x204) || (iVar4 == 0x100)) || (iVar4 == 0x201)) {
LAB_005e4f6e:
        iVar4 = param_1[0xaf];
        QueryPerformanceCounter(&uStack_28);
        *(undefined1 *)(iVar4 + 0x2db0) = 0;
        *(double *)(iVar4 + 0x2da8) = (double)CONCAT44(uStack_24,uStack_28);
      }
    }
    else if (iVar4 == 0x20a) goto LAB_005e4f6e;
    if (param_2[1] == 0x200) {
      *(undefined1 *)(param_1[0xaf] + 0x2db0) = 0;
    }
    if (param_2[1] == 0x1c) {
      uVar5 = param_2[2];
      *(char *)(param_1 + 0x375) = (char)uVar5;
      if ((char)uVar5 == '\0') {
        iVar4 = param_1[0xaf];
        *(undefined1 *)(iVar4 + 0x618) = 1;
        if (*(char *)(iVar4 + 0x638) == '\0') {
          (**(code **)(*(int *)(iVar4 + 0xf8) + 0x24))();
        }
      }
      else {
        func_0x004e9d90();
        SetEvent(*(undefined4 *)(*(int *)(param_1[0xaf] + 0x2db4) + 0x70));
        uStack_1c = 0;
        uStack_18 = 0;
        uStack_14 = 0;
        uStack_10 = 0;
        uStack_20 = 0x14;
        iVar4 = (**(code **)(*param_1 + 0x24))();
        uStack_1c = *(undefined4 *)(iVar4 + 0x6c);
        uStack_14 = 0;
        uStack_18 = 0;
        FlashWindowEx(&uStack_20);
      }
    }
    if (param_2[1] != 0x4a) {
LAB_005e5056:
      iVar4 = func_0x00a527b0(param_2);
      return iVar4;
    }
LAB_005e4f3d:
    iVar4 = func_0x00601090(param_2);
    return iVar4;
  }
  uStack_28 = param_2[3];
  uVar1 = *(ushort *)(param_2 + 2);
  if ((*(short *)((int)param_2 + 10) == -1) && (uStack_28 == 0)) goto LAB_005e5056;
  param_1[0x38d] = -1;
  param_1[0x38c] = -1;
  param_1[0x390] = -1;
  uStack_24 = uStack_24 & 0xffffff00;
  if (uVar1 < 48000) {
    if (uVar1 < 49000) goto LAB_005e4ca4;
LAB_005e4c8c:
    if (49999 < uVar1) goto LAB_005e4ca4;
  }
  else if (48999 < uVar1) goto LAB_005e4c8c;
  iVar4 = func_0x005c6670();
  param_1[0x390] = iVar4;
LAB_005e4ca4:
  if ((ushort)(uVar1 + 0x5038) < 0x7d1) {
    iVar4 = func_0x005c6670();
    if (uVar1 < 46000) {
      param_1[0x38c] = iVar4;
    }
    else {
      param_1[0x38d] = iVar4;
    }
  }
  iVar4 = func_0x00a527b0(param_2);
  func_0x005132f0();
  return iVar4;
}


