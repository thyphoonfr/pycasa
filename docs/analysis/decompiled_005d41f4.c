// Address: 005d3290
// Function: FUN_005d3290
// Target requested: 0x005d41f4

/* WARNING: Type propagation algorithm not settling */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

int FUN_005d3290(int param_1,int param_2)

{
  int **ppiVar1;
  byte bVar2;
  char cVar3;
  char cVar4;
  char *pcVar5;
  undefined4 uVar6;
  int ***pppiVar7;
  int *piVar8;
  int **ppiVar9;
  int iVar10;
  int iVar11;
  uint uVar12;
  int iVar13;
  uint *unaff_EBX;
  int unaff_EBP;
  uint unaff_ESI;
  int ***pppiVar14;
  undefined4 *puVar15;
  char *pcVar16;
  uint *puVar17;
  bool bVar18;
  int unaff_retaddr;
  int ****ppppiStack_180;
  int ****ppppiStack_17c;
  int ***pppiStack_178;
  undefined4 *puStack_174;
  undefined4 *puStack_170;
  int **ppiStack_15c;
  undefined4 uStack_158;
  undefined4 uStack_154;
  undefined4 uStack_150;
  int **ppiStack_14c;
  int ***pppiStack_148;
  int aiStack_144 [2];
  uint *puStack_13c;
  int ***pppiStack_138;
  undefined4 uStack_134;
  char cStack_130;
  char cStack_12f;
  int iStack_11c;
  int iStack_118;
  undefined4 uStack_90;
  int **ppiStack_8c;
  int iStack_88;
  int ***pppiStack_84;
  int **ppiStack_80;
  int **ppiStack_7c;
  undefined *puStack_78;
  undefined4 uStack_74;
  undefined4 uStack_70;
  undefined4 uStack_68;
  int **ppiStack_64;
  int iStack_60;
  int **ppiStack_5c;
  int iStack_58;
  int iStack_54;
  undefined1 auStack_4c [8];
  undefined1 uStack_44;
  undefined1 uStack_43;
  undefined1 uStack_42;
  undefined1 uStack_41;
  undefined1 uStack_40;
  undefined1 uStack_3f;
  undefined1 uStack_3e;
  undefined1 uStack_3d;
  undefined4 uStack_3c;
  undefined4 uStack_38;
  undefined4 uStack_34;
  int iStack_1c;
  int *piStack_14;
  int ***pppiStack_c;
  int iStack_8;
  int ***pppiStack_4;
  
  ppiStack_14c = (int **)0x0;
  iVar13 = *(int *)(param_2 + 0x14);
  pppiStack_178 = *(int ****)(param_2 + 0x24);
  aiStack_144[0] = (int)pppiStack_178;
  if (iVar13 != 0) {
    if (iVar13 == -4) {
      if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005d3376;
      bVar18 = false;
    }
    else {
      if (iVar13 == 0) {
        pcVar5 = (char *)0x0;
      }
      else {
        pcVar5 = (char *)(iVar13 + 4);
      }
      iVar13 = 6;
      bVar18 = true;
      pcVar16 = "lb_up";
      do {
        if (iVar13 == 0) break;
        iVar13 = iVar13 + -1;
        bVar18 = *pcVar16 == *pcVar5;
        pcVar16 = pcVar16 + 1;
        pcVar5 = pcVar5 + 1;
      } while (bVar18);
    }
    if (bVar18) {
      if (((pppiStack_178 != (int ***)0x0) &&
          (puStack_174 = (undefined4 *)(*(int *)((int)pppiStack_178 + 0x2f8) + -1),
          (int)puStack_174 < (int)(*(uint *)((int)pppiStack_178 + 0x298) >> 1))) &&
         (-1 < (int)puStack_174)) {
        puStack_170 = (undefined4 *)0x1;
        *(undefined4 **)((int)pppiStack_178 + 0x30c) = puStack_174;
        ppppiStack_17c = (int ****)0x5d3332;
        func_0x009d2810();
      }
      ppppiStack_17c = (int ****)0xffffffff;
      ppppiStack_180 = (int ****)0x1;
      pppiStack_178 = (int ***)0xffffffff;
      puStack_174 = (undefined4 *)0xffffffff;
      puStack_170 = (undefined4 *)0xffffffff;
      func_0x00a54b70(param_1,1,1,0);
      return 0xf4241;
    }
  }
LAB_005d3376:
  iVar13 = *(int *)(param_2 + 0x14);
  if (iVar13 != 0) {
    if (iVar13 == -4) {
      if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005d3417;
      bVar18 = false;
    }
    else {
      if (iVar13 == 0) {
        pcVar5 = (char *)0x0;
      }
      else {
        pcVar5 = (char *)(iVar13 + 4);
      }
      iVar13 = 8;
      bVar18 = true;
      pcVar16 = "lb_down";
      do {
        if (iVar13 == 0) break;
        iVar13 = iVar13 + -1;
        bVar18 = *pcVar16 == *pcVar5;
        pcVar16 = pcVar16 + 1;
        pcVar5 = pcVar5 + 1;
      } while (bVar18);
    }
    if (bVar18) {
      if (pppiStack_178 != (int ***)0x0) {
        puStack_170 = (undefined4 *)0x1;
        puStack_174 = (undefined4 *)0x5d33d3;
        func_0x009d21e0();
      }
      ppppiStack_17c = (int ****)0xffffffff;
      ppppiStack_180 = (int ****)0x1;
      pppiStack_178 = (int ***)0xffffffff;
      puStack_174 = (undefined4 *)0xffffffff;
      puStack_170 = (undefined4 *)0xffffffff;
      func_0x00a54b70(param_1,1,1,0);
      return 0xf4241;
    }
  }
LAB_005d3417:
  if (_DAT_00d67914 == 0) {
    uStack_158 = 0;
  }
  else {
    puStack_170 = &uStack_158;
    puStack_174 = (undefined4 *)0x5d342b;
    func_0x009c2f50();
  }
  puStack_170 = (undefined4 *)0x0;
  puStack_174 = (undefined4 *)0x5d3440;
  cVar3 = func_0x00987030();
  puStack_174 = (undefined4 *)0x5d344b;
  func_0x00401000();
  if (cVar3 != '\0') {
    iVar13 = *(int *)(param_1 + 0x14);
    if (iVar13 != 0) {
      if (iVar13 == -4) {
        if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005d35ab;
        bVar18 = false;
      }
      else {
        if (iVar13 == 0) {
          pcVar5 = (char *)0x0;
        }
        else {
          pcVar5 = (char *)(iVar13 + 4);
        }
        iVar13 = 0xc;
        bVar18 = true;
        pcVar16 = "lb_preclick";
        do {
          if (iVar13 == 0) break;
          iVar13 = iVar13 + -1;
          bVar18 = *pcVar16 == *pcVar5;
          pcVar16 = pcVar16 + 1;
          pcVar5 = pcVar5 + 1;
        } while (bVar18);
      }
      if ((bVar18) && (*(int *)(param_1 + 0xc) != -1)) {
        if ((int)pppiStack_148[200] + (int)pppiStack_148[0xbe] != *(int *)(param_1 + 0xc)) {
          pppiStack_178 = (int ***)0x5d34f2;
          iVar13 = func_0x005e45c0();
          if (iVar13 == 0) {
            if ((((*(char *)(unaff_retaddr + 0x318) == '\0') &&
                 (uVar12 = *(uint *)(unaff_retaddr + 0x3378), 2 < uVar12)) && (uVar12 < 6)) &&
               (iVar13 = *(int *)(unaff_retaddr + 0x33a0 + uVar12 * 4), iVar13 != 0)) {
              if (*(uint *)(param_1 + 0xc) < *(uint *)(iVar13 + 0x10) >> 1) {
                pppiStack_178 = (int ***)0x5d3542;
                func_0x0050bf30();
                if (((unaff_EBX != (uint *)0x0) && ((*unaff_EBX & 0xffffff00) != 0)) &&
                   (pppiStack_178 = (int ***)(unaff_EBX + 1), (char)*pppiStack_178 != '\0')) {
                  ppppiStack_17c = (int ****)0x5d3562;
                  iVar13 = func_0x006021d0();
                  if (iVar13 != 0) {
                    pppiStack_178 = (int ***)0x5d3571;
                    func_0x00401000();
                    return iVar13;
                  }
                }
              }
              pppiStack_178 = (int ***)0x5d358d;
              func_0x00401000();
            }
            pppiStack_178 = (int ***)0x1;
            ppppiStack_17c = (int ****)0x5d3599;
            func_0x009d2550();
          }
        }
        return 1000000;
      }
    }
LAB_005d35ab:
    iVar13 = *(int *)(param_1 + 0x14);
    if (iVar13 != 0) {
      if (iVar13 == -4) {
        if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005d362c;
        bVar18 = false;
      }
      else {
        if (iVar13 == 0) {
          pcVar5 = (char *)0x0;
        }
        else {
          pcVar5 = (char *)(iVar13 + 4);
        }
        iVar13 = 0xc;
        bVar18 = true;
        pcVar16 = "lb_selected";
        do {
          if (iVar13 == 0) break;
          iVar13 = iVar13 + -1;
          bVar18 = *pcVar16 == *pcVar5;
          pcVar16 = pcVar16 + 1;
          pcVar5 = pcVar5 + 1;
        } while (bVar18);
      }
      if (bVar18) {
        if (-1 < (int)pppiStack_148[200] + (int)pppiStack_148[0xbe]) {
          pppiStack_148[0xc3] = (int **)((int)pppiStack_148[200] + (int)pppiStack_148[0xbe]);
        }
        return 1000000;
      }
    }
  }
LAB_005d362c:
  if (_DAT_00d67914 == 0) {
    uVar6 = 0;
  }
  else {
    puStack_174 = (undefined4 *)0x5d363e;
    uVar6 = func_0x009c2fc0();
  }
  puStack_174 = (undefined4 *)0x0;
  pppiStack_178 = (int ***)0xd3b8f4;
  ppppiStack_17c = (int ****)0xd3b8a0;
  ppppiStack_180 = (int ****)0x0;
  iVar13 = func_0x00c07db2(uVar6);
  if (iVar13 != 0) {
    if (*(int *)(iVar13 + 0x3f8) == 0) {
      pppiVar7 = (int ***)0x0;
    }
    else {
      pppiVar7 = *(int ****)(*(int *)(iVar13 + 0x3f8) + 0x278);
    }
    if (pppiStack_148 == pppiVar7) {
      iVar13 = *(int *)(param_1 + 0x14);
      if (iVar13 != 0) {
        if (iVar13 == -4) {
          if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005d3717;
          bVar18 = false;
        }
        else {
          if (iVar13 == 0) {
            pcVar5 = (char *)0x0;
          }
          else {
            pcVar5 = (char *)(iVar13 + 4);
          }
          iVar13 = 0xc;
          bVar18 = true;
          pcVar16 = "lb_endpopup";
          do {
            if (iVar13 == 0) break;
            iVar13 = iVar13 + -1;
            bVar18 = *pcVar16 == *pcVar5;
            pcVar16 = pcVar16 + 1;
            pcVar5 = pcVar5 + 1;
          } while (bVar18);
        }
        if (bVar18) {
          ppppiStack_180 = (int ****)0xffffffff;
          ppppiStack_17c = (int ****)0xffffffff;
          pppiStack_178 = (int ***)0xffffffff;
          puStack_174 = (undefined4 *)0xffffffff;
          func_0x00a54b70(unaff_retaddr,1,1,0,1);
          func_0x009cd8a0();
          goto LAB_005d37c6;
        }
      }
LAB_005d3717:
      iVar13 = *(int *)(param_1 + 0x14);
      if (iVar13 != 0) {
        if (iVar13 == -4) {
          if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005d376e;
          bVar18 = false;
        }
        else {
          if (iVar13 == 0) {
            pcVar5 = (char *)0x0;
          }
          else {
            pcVar5 = (char *)(iVar13 + 4);
          }
          iVar13 = 0xf;
          bVar18 = true;
          pcVar16 = "lb_cancelpopup";
          do {
            if (iVar13 == 0) break;
            iVar13 = iVar13 + -1;
            bVar18 = *pcVar16 == *pcVar5;
            pcVar16 = pcVar16 + 1;
            pcVar5 = pcVar5 + 1;
          } while (bVar18);
        }
        if (bVar18) {
          puStack_174 = (undefined4 *)0x0;
          pppiStack_178 = (int ***)0xffffffff;
          ppppiStack_17c = (int ****)pppiStack_148;
          ppppiStack_180 = (int ****)0x5d376c;
          func_0x009d2810();
          goto LAB_005d37c6;
        }
      }
LAB_005d376e:
      iVar13 = *(int *)(param_1 + 0x14);
      if (iVar13 != 0) {
        if (iVar13 == -4) {
          if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005d37c6;
          bVar18 = false;
        }
        else {
          if (iVar13 == 0) {
            pcVar5 = (char *)0x0;
          }
          else {
            pcVar5 = (char *)(iVar13 + 4);
          }
          iVar13 = 9;
          bVar18 = true;
          pcVar16 = "lb_hover";
          do {
            if (iVar13 == 0) break;
            iVar13 = iVar13 + -1;
            bVar18 = *pcVar16 == *pcVar5;
            pcVar16 = pcVar16 + 1;
            pcVar5 = pcVar5 + 1;
          } while (bVar18);
        }
        if (bVar18) {
          puStack_174 = (undefined4 *)0x0;
          pppiStack_178 = (int ***)0x5d37c6;
          func_0x009d2550();
        }
      }
    }
  }
LAB_005d37c6:
  if (_DAT_00d67914 == 0) {
    uVar6 = 0;
  }
  else {
    puStack_174 = (undefined4 *)0x5d37d8;
    uVar6 = func_0x009c2fc0();
  }
  puStack_174 = (undefined4 *)0x0;
  pppiStack_178 = (int ***)0xd3b8f4;
  ppppiStack_17c = (int ****)0xd3b8a0;
  ppppiStack_180 = (int ****)0x0;
  iVar13 = func_0x00c07db2(uVar6);
  if (iVar13 != 0) {
    if (*(int *)(iVar13 + 0x3f8) == 0) {
      pppiVar7 = (int ***)0x0;
    }
    else {
      pppiVar7 = *(int ****)(*(int *)(iVar13 + 0x3f8) + 0x278);
    }
    if (pppiStack_148 == pppiVar7) {
      iVar13 = *(int *)(param_1 + 0x14);
      if (iVar13 != 0) {
        if (iVar13 == -4) {
          if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005d38db;
          bVar18 = false;
        }
        else {
          if (iVar13 == 0) {
            pcVar5 = (char *)0x0;
          }
          else {
            pcVar5 = (char *)(iVar13 + 4);
          }
          iVar13 = 0xc;
          bVar18 = true;
          pcVar16 = "lb_endpopup";
          do {
            if (iVar13 == 0) break;
            iVar13 = iVar13 + -1;
            bVar18 = *pcVar16 == *pcVar5;
            pcVar16 = pcVar16 + 1;
            pcVar5 = pcVar5 + 1;
          } while (bVar18);
        }
        if (bVar18) {
          ppppiStack_180 = (int ****)0xffffffff;
          ppppiStack_17c = (int ****)0xffffffff;
          pppiStack_178 = (int ***)0xffffffff;
          puStack_174 = (undefined4 *)0xffffffff;
          func_0x00a54b70(unaff_retaddr,1,1,0,1);
          ppppiStack_180 = (int ****)0x0;
          iVar13 = func_0x005c6590();
          func_0x0040eab0(&UNK_00c95df0,*(undefined4 *)(iVar13 + 4));
          func_0x00679ca0(unaff_retaddr,&ppppiStack_180);
          func_0x00401000();
          goto LAB_005d3999;
        }
      }
LAB_005d38db:
      iVar13 = *(int *)(param_1 + 0x14);
      if (iVar13 != 0) {
        if (iVar13 == -4) {
          if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005d393d;
          bVar18 = false;
        }
        else {
          if (iVar13 == 0) {
            pcVar5 = (char *)0x0;
          }
          else {
            pcVar5 = (char *)(iVar13 + 4);
          }
          iVar13 = 0xf;
          bVar18 = true;
          pcVar16 = "lb_cancelpopup";
          do {
            if (iVar13 == 0) break;
            iVar13 = iVar13 + -1;
            bVar18 = *pcVar16 == *pcVar5;
            pcVar16 = pcVar16 + 1;
            pcVar5 = pcVar5 + 1;
          } while (bVar18);
        }
        if (bVar18) {
          puStack_174 = (undefined4 *)0x0;
          pppiStack_178 = (int ***)0xffffffff;
          ppppiStack_17c = (int ****)pppiStack_148;
          ppppiStack_180 = (int ****)0x5d393b;
          func_0x009d2810();
          goto LAB_005d3999;
        }
      }
LAB_005d393d:
      iVar13 = *(int *)(param_1 + 0x14);
      if (iVar13 != 0) {
        if (iVar13 == -4) {
          if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005d3999;
          bVar18 = false;
        }
        else {
          if (iVar13 == 0) {
            pcVar5 = (char *)0x0;
          }
          else {
            pcVar5 = (char *)(iVar13 + 4);
          }
          iVar13 = 9;
          bVar18 = true;
          pcVar16 = "lb_hover";
          do {
            if (iVar13 == 0) break;
            iVar13 = iVar13 + -1;
            bVar18 = *pcVar16 == *pcVar5;
            pcVar16 = pcVar16 + 1;
            pcVar5 = pcVar5 + 1;
          } while (bVar18);
        }
        if (bVar18) {
          puStack_174 = (undefined4 *)0x0;
          pppiStack_178 = (int ***)0x5d3999;
          func_0x009d2550();
        }
      }
    }
  }
LAB_005d3999:
  bVar18 = false;
  if (_DAT_00d67914 == 0) {
    uStack_150 = 0;
  }
  else {
    puStack_174 = &uStack_150;
    pppiStack_178 = (int ***)0x5d39b6;
    func_0x009c2f50();
  }
  puStack_174 = (undefined4 *)0x0;
  pppiStack_178 = (int ***)0x5d39cb;
  cVar3 = func_0x00987030();
  if (cVar3 == '\0') {
    bVar18 = true;
    if (_DAT_00d67914 != 0) {
      pppiStack_178 = (int ***)&stack0xfffffea0;
      ppppiStack_17c = (int ****)0x5d39e8;
      func_0x009c2f50();
    }
    pppiStack_178 = (int ***)0x0;
    ppppiStack_17c = (int ****)0x5d39fd;
    cVar3 = func_0x00987030();
    uStack_158 = uStack_158 & 0xffffff;
    if (cVar3 != '\0') goto LAB_005d3a06;
  }
  else {
LAB_005d3a06:
    uStack_158 = CONCAT13(1,(undefined3)uStack_158);
  }
  if (bVar18) {
    pppiStack_178 = (int ***)0x5d3a1c;
    func_0x00401000();
  }
  pppiStack_178 = (int ***)0x5d3a2a;
  func_0x00401000();
  if (uStack_158._3_1_ != '\0') {
    ppppiStack_17c = (int ****)pppiStack_4;
    ppppiStack_180 = (int ****)0x5d3a46;
    func_0x0067b7e0();
  }
  if (_DAT_00d67914 == 0) {
    uVar6 = 0;
  }
  else {
    pppiStack_178 = (int ***)0x5d3a58;
    uVar6 = func_0x009c2fc0();
  }
  pppiStack_178 = (int ***)0x0;
  ppppiStack_17c = (int ****)0xd3b8f4;
  ppppiStack_180 = (int ****)0xd3b8a0;
  iVar13 = func_0x00c07db2(uVar6,0);
  if (iVar13 != 0) {
    if (*(int *)(iVar13 + 0x3f8) == 0) {
      pppiVar7 = (int ***)0x0;
    }
    else {
      pppiVar7 = *(int ****)(*(int *)(iVar13 + 0x3f8) + 0x278);
    }
    if (pppiStack_148 == pppiVar7) {
      ppppiStack_17c = (int ****)pppiStack_4;
      ppppiStack_180 = (int ****)0x5d3aa2;
      func_0x00760b00();
    }
  }
  if (_DAT_00d67914 == 0) {
    uVar6 = 0;
  }
  else {
    pppiStack_178 = (int ***)0x5d3ab4;
    uVar6 = func_0x009c2fc0();
  }
  pppiStack_178 = (int ***)0x0;
  ppppiStack_17c = (int ****)0xd3b8f4;
  ppppiStack_180 = (int ****)0xd3b8a0;
  piVar8 = (int *)func_0x00c07db2(uVar6,0);
  if (piVar8 != (int *)0x0) {
    if (piVar8[0xfe] == 0) {
      ppiVar9 = (int **)0x0;
    }
    else {
      ppiVar9 = *(int ***)(piVar8[0xfe] + 0x278);
    }
    if (ppiStack_14c == ppiVar9) {
      iVar13 = *(int *)(unaff_retaddr + 0x14);
      if (iVar13 == 0) {
LAB_005d3b82:
        iVar13 = *(int *)(unaff_retaddr + 0x14);
        if (iVar13 != 0) {
          if (iVar13 == -4) {
            if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005d3c0c;
            bVar18 = false;
          }
          else {
            if (iVar13 == 0) {
              pcVar5 = (char *)0x0;
            }
            else {
              pcVar5 = (char *)(iVar13 + 4);
            }
            iVar13 = 0xf;
            bVar18 = true;
            pcVar16 = "lb_preselected";
            do {
              if (iVar13 == 0) break;
              iVar13 = iVar13 + -1;
              bVar18 = *pcVar16 == *pcVar5;
              pcVar16 = pcVar16 + 1;
              pcVar5 = pcVar5 + 1;
            } while (bVar18);
          }
          if (bVar18) {
            pppiStack_178 = (int ***)0x5d3be1;
            piVar8 = (int *)func_0x00512e20();
            if (piVar8 != (int *)0x0) {
              pppiStack_178 = (int ***)0x5d3bf2;
              cVar3 = (**(code **)(*piVar8 + 0xc))();
              if (cVar3 != '\0') {
                return 1000000;
              }
            }
            return 0xf4241;
          }
        }
LAB_005d3c0c:
        iVar13 = *(int *)(unaff_retaddr + 0x14);
        if (iVar13 != 0) {
          if (iVar13 == -4) {
            if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005d3d06;
            bVar18 = false;
          }
          else {
            if (iVar13 == 0) {
              pcVar5 = (char *)0x0;
            }
            else {
              pcVar5 = (char *)(iVar13 + 4);
            }
            iVar13 = 0xc;
            bVar18 = true;
            pcVar16 = "lb_endpopup";
            do {
              if (iVar13 == 0) break;
              iVar13 = iVar13 + -1;
              bVar18 = *pcVar16 == *pcVar5;
              pcVar16 = pcVar16 + 1;
              pcVar5 = pcVar5 + 1;
            } while (bVar18);
          }
          if ((bVar18) && ((int)ppiStack_14c[200] + (int)ppiStack_14c[0xbe] != -1)) {
            pppiStack_178 = (int ***)0x0;
            ppppiStack_17c = (int ****)0xd3f874;
            ppppiStack_180 = (int ****)0xd3b740;
            iVar13 = func_0x00c07db2(piVar8[0x100],0);
            if (iVar13 != 0) {
              pppiStack_178 = (int ***)0x5d3cad;
              iVar11 = func_0x007cc320();
              pppiStack_178 = (int ***)0x5d3cb6;
              iVar10 = func_0x00512e50();
              if (iVar10 == iVar11) {
                ppppiStack_17c = (int ****)0x5d3cc7;
                pppiStack_178 = (int ***)iVar13;
                func_0x007cf6c0();
                ppppiStack_17c = (int ****)0x5d3cce;
                iVar13 = func_0x008d26a0();
                if (iVar13 != 0) {
                  ppppiStack_17c = (int ****)0x0;
                  ppppiStack_180 = (int ****)0x5d3cdf;
                  (**(code **)(*piVar8 + 0x80))();
                  ppppiStack_180 = (int ****)0x5d3ce8;
                  func_0x009d2550();
                }
                ppppiStack_17c = (int ****)0x5d3cf4;
                func_0x007cf800();
              }
            }
            pppiStack_178 = pppiStack_4;
            ppppiStack_17c = (int ****)0x5d3d01;
            func_0x005f01d0();
            goto LAB_005d3de0;
          }
        }
LAB_005d3d06:
        iVar13 = *(int *)(unaff_retaddr + 0x14);
        if (iVar13 != 0) {
          if (iVar13 == -4) {
            if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005d3d60;
            bVar18 = false;
          }
          else {
            if (iVar13 == 0) {
              pcVar5 = (char *)0x0;
            }
            else {
              pcVar5 = (char *)(iVar13 + 4);
            }
            iVar13 = 0xe;
            bVar18 = true;
            pcVar16 = "lb_beginpopup";
            do {
              if (iVar13 == 0) break;
              iVar13 = iVar13 + -1;
              bVar18 = *pcVar16 == *pcVar5;
              pcVar16 = pcVar16 + 1;
              pcVar5 = pcVar5 + 1;
            } while (bVar18);
          }
          if (bVar18) {
            pppiStack_178 = (int ***)0x5d3d5b;
            (**(code **)(*piVar8 + 0x7c))();
            goto LAB_005d3de0;
          }
        }
LAB_005d3d60:
        iVar13 = *(int *)(unaff_retaddr + 0x14);
        if (iVar13 != 0) {
          if (iVar13 == -4) {
            if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005d3de0;
            bVar18 = false;
          }
          else {
            if (iVar13 == 0) {
              pcVar5 = (char *)0x0;
            }
            else {
              pcVar5 = (char *)(iVar13 + 4);
            }
            iVar13 = 0xf;
            bVar18 = true;
            pcVar16 = "lb_cancelpopup";
            do {
              if (iVar13 == 0) break;
              iVar13 = iVar13 + -1;
              bVar18 = *pcVar16 == *pcVar5;
              pcVar16 = pcVar16 + 1;
              pcVar5 = pcVar5 + 1;
            } while (bVar18);
          }
          if (bVar18) {
            pppiStack_178 = (int ***)0x5d3db8;
            iVar13 = (**(code **)(*piVar8 + 0x80))();
            if (iVar13 != -1) {
              pppiStack_178 = (int ***)0x5d3dc6;
              func_0x0040a2c0();
              pppiStack_178 = (int ***)0x5d3dcf;
              func_0x009d2580();
              pppiStack_178 = (int ***)0x0;
              ppppiStack_17c = (int ****)0x5d3dd7;
              func_0x0040a2c0();
              goto LAB_005d3ddb;
            }
          }
        }
      }
      else {
        if (iVar13 == -4) {
          if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005d3b82;
          bVar18 = false;
        }
        else {
          if (iVar13 == 0) {
            pcVar5 = (char *)0x0;
          }
          else {
            pcVar5 = (char *)(iVar13 + 4);
          }
          iVar13 = 9;
          bVar18 = true;
          pcVar16 = "lb_hover";
          do {
            if (iVar13 == 0) break;
            iVar13 = iVar13 + -1;
            bVar18 = *pcVar16 == *pcVar5;
            pcVar16 = pcVar16 + 1;
            pcVar5 = pcVar5 + 1;
          } while (bVar18);
        }
        if (!bVar18) goto LAB_005d3b82;
        pppiStack_178 = (int ***)0x5d3b59;
        piVar8 = (int *)func_0x00512e20();
        if (piVar8 == (int *)0x0) goto LAB_005d3de0;
        pppiStack_178 = (int ***)0x5d3b6a;
        cVar3 = (**(code **)(*piVar8 + 0xc))();
        if (cVar3 != '\0') goto LAB_005d3de0;
        pppiStack_178 = (int ***)0x0;
LAB_005d3ddb:
        ppppiStack_17c = (int ****)0x5d3de0;
        func_0x009d2550();
      }
    }
  }
LAB_005d3de0:
  pppiVar7 = pppiStack_4;
  if (ppiStack_14c != pppiStack_4[0x3ac]) {
    return 0;
  }
  iVar13 = *(int *)(unaff_retaddr + 0x14);
  if (iVar13 != 0) {
    if (iVar13 == -4) {
      if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005d3f01;
      bVar18 = false;
    }
    else {
      if (iVar13 == 0) {
        pcVar5 = (char *)0x0;
      }
      else {
        pcVar5 = (char *)(iVar13 + 4);
      }
      iVar13 = 0xc;
      bVar18 = true;
      pcVar16 = "lb_selected";
      do {
        if (iVar13 == 0) break;
        iVar13 = iVar13 + -1;
        bVar18 = *pcVar16 == *pcVar5;
        pcVar16 = pcVar16 + 1;
        pcVar5 = pcVar5 + 1;
      } while (bVar18);
    }
    if (bVar18) {
      if (_DAT_00d67914 == 0) {
        uVar6 = 0;
      }
      else {
        pppiStack_178 = (int ***)0x5d3e70;
        uVar6 = func_0x009c2fc0();
      }
      pppiStack_178 = (int ***)0x0;
      ppppiStack_17c = (int ****)0xd3b914;
      ppppiStack_180 = (int ****)0xd3b8a0;
      piVar8 = (int *)func_0x00c07db2(uVar6,0);
      if (piVar8 != (int *)0x0) {
        pppiStack_178 = (int ***)&UNK_00c95e70;
        uStack_154 = 0;
        ppppiStack_17c = (int ****)0x5d3ea6;
        func_0x00985ff0();
        ppppiStack_180 = (int ****)0x5d3eb2;
        ppppiStack_17c = (int ****)&uStack_154;
        (**(code **)(*piVar8 + 0x7c))();
        ppppiStack_180 = (int ****)0x5d3eb7;
        func_0x00401000();
      }
      ppppiStack_180 = (int ****)0xffffffff;
      ppppiStack_17c = (int ****)0xffffffff;
      pppiStack_178 = (int ***)0xffffffff;
      func_0x00a54b70(pppiStack_4,1,1,0,1,0xffffffff);
      func_0x006dcc40(pppiStack_4);
      return 0xf4241;
    }
  }
LAB_005d3f01:
  iVar13 = *(int *)(unaff_retaddr + 0x14);
  if (iVar13 != 0) {
    if (iVar13 == -4) {
      if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005d3f69;
      bVar18 = false;
    }
    else {
      if (iVar13 == 0) {
        pcVar5 = (char *)0x0;
      }
      else {
        pcVar5 = (char *)(iVar13 + 4);
      }
      iVar13 = 8;
      bVar18 = true;
      pcVar16 = "lb_drop";
      do {
        if (iVar13 == 0) break;
        iVar13 = iVar13 + -1;
        bVar18 = *pcVar16 == *pcVar5;
        pcVar16 = pcVar16 + 1;
        pcVar5 = pcVar5 + 1;
      } while (bVar18);
    }
    if (bVar18) {
      pppiStack_178 = pppiStack_4;
      ppppiStack_17c = (int ****)0x5d3f5c;
      iVar13 = func_0x005e39a0();
      return iVar13;
    }
  }
LAB_005d3f69:
  iVar13 = *(int *)(unaff_retaddr + 0x14);
  if (iVar13 != 0) {
    if (iVar13 == -4) {
      if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005d3fe2;
      bVar18 = false;
    }
    else {
      if (iVar13 == 0) {
        pcVar5 = (char *)0x0;
      }
      else {
        pcVar5 = (char *)(iVar13 + 4);
      }
      iVar13 = 0x15;
      bVar18 = true;
      pcVar16 = "lb_controlmousewheel";
      do {
        if (iVar13 == 0) break;
        iVar13 = iVar13 + -1;
        bVar18 = *pcVar16 == *pcVar5;
        pcVar16 = pcVar16 + 1;
        pcVar5 = pcVar5 + 1;
      } while (bVar18);
    }
    if (bVar18) {
      if (*(int *)(unaff_retaddr + 8) == 0) {
        pppiStack_178 = (int ***)0x5d3fd9;
        (*(code *)pppiStack_4[0xa9][0xf])();
      }
      else {
        pppiStack_178 = (int ***)0x5d3fd2;
        (*(code *)pppiStack_4[0xa9][0x10])();
      }
    }
  }
LAB_005d3fe2:
  iVar13 = *(int *)(unaff_retaddr + 0x14);
  if (iVar13 == 0) {
LAB_005d4039:
    iVar13 = *(int *)(unaff_retaddr + 0x14);
    if (iVar13 != 0) {
      if (iVar13 == -4) {
        if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005d4089;
        bVar18 = false;
      }
      else {
        if (iVar13 == 0) {
          pcVar5 = (char *)0x0;
        }
        else {
          pcVar5 = (char *)(iVar13 + 4);
        }
        iVar13 = 0xd;
        bVar18 = true;
        pcVar16 = "lb_predouble";
        do {
          if (iVar13 == 0) break;
          iVar13 = iVar13 + -1;
          bVar18 = *pcVar16 == *pcVar5;
          pcVar16 = pcVar16 + 1;
          pcVar5 = pcVar5 + 1;
        } while (bVar18);
      }
      if (bVar18) goto LAB_005d47a8;
    }
LAB_005d4089:
    iVar13 = *(int *)(unaff_retaddr + 0x14);
    if (iVar13 != 0) {
      if (iVar13 == -4) {
        if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005d40d9;
        bVar18 = false;
      }
      else {
        if (iVar13 == 0) {
          pcVar5 = (char *)0x0;
        }
        else {
          pcVar5 = (char *)(iVar13 + 4);
        }
        iVar13 = 0xc;
        bVar18 = true;
        pcVar16 = "lb_activate";
        do {
          if (iVar13 == 0) break;
          iVar13 = iVar13 + -1;
          bVar18 = *pcVar16 == *pcVar5;
          pcVar16 = pcVar16 + 1;
          pcVar5 = pcVar5 + 1;
        } while (bVar18);
      }
      if (bVar18) goto LAB_005d47a8;
    }
LAB_005d40d9:
    pppiStack_178 = (int ***)0x5d40e2;
    func_0x004a06e0();
    iVar13 = *(int *)(unaff_retaddr + 0x14);
    if (iVar13 != 0) {
      if (iVar13 == -4) {
        if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005d4407;
        bVar18 = false;
      }
      else {
        if (iVar13 == 0) {
          pcVar5 = (char *)0x0;
        }
        else {
          pcVar5 = (char *)(iVar13 + 4);
        }
        iVar13 = 0xe;
        bVar18 = true;
        pcVar16 = "lb_rightclick";
        do {
          if (iVar13 == 0) break;
          iVar13 = iVar13 + -1;
          bVar18 = *pcVar16 == *pcVar5;
          pcVar16 = pcVar16 + 1;
          pcVar5 = pcVar5 + 1;
        } while (bVar18);
      }
      if (bVar18) {
        ppiStack_14c = *(int ***)(unaff_retaddr + 0x18);
        pppiStack_148 = *(int ****)(unaff_retaddr + 0x1c);
        pppiStack_4[0x38e] = (int **)0xffffffff;
        pppiStack_4[0x38f] = (int **)0xffffffff;
        ppiVar9 = *(int ***)(unaff_retaddr + 0xc);
        pppiStack_178 = (int ***)aiStack_144;
        ppppiStack_180 = (int ****)0x5d4188;
        ppppiStack_17c = (int ****)ppiVar9;
        iVar13 = func_0x004ae4e0();
        if (iVar13 != 0) {
LAB_005d4204:
          ppppiStack_180 = (int ****)0x5d420d;
          func_0x004abb70();
          return iVar13;
        }
        if (pppiStack_c[0xc3d] != (int **)0x0) {
          if (iStack_11c == 0) {
            pppiStack_c[0x38e] = (int **)pppiStack_138;
          }
          else if (iStack_11c != 3) goto LAB_005d41aa;
          pppiStack_c[0x38f] = ppiVar9;
          ppppiStack_180 = (int ****)0x5d41e0;
          func_0x007325a0();
          ppppiStack_180 = (int ****)0x5d41e9;
          (*(code *)(*pppiStack_c)[9])();
          ppppiStack_180 = (int ****)0x0;
          iVar13 = FUN_005e7c20(&ppiStack_15c);
          func_0x005132f0();
          goto LAB_005d4204;
        }
        if (((uStack_134._2_1_ != '\0') || (iStack_11c == 3)) || (iStack_11c == 8)) {
LAB_005d41aa:
          ppppiStack_180 = (int ****)0x5d41b3;
          func_0x004abb70();
          return 1000000;
        }
        ppppiStack_180 = (int ****)0x5d4242;
        func_0x007319f0();
        pppiVar7 = pppiStack_c;
        if (iStack_11c == 0) {
          if (puStack_13c != (uint *)0x0) {
            if (puStack_13c + 1 == (uint *)0x0) {
              if (((*puStack_13c & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005d42ab;
              bVar18 = false;
            }
            else {
              iVar13 = 7;
              bVar18 = true;
              pcVar5 = "People";
              puVar17 = puStack_13c + 1;
              do {
                if (iVar13 == 0) break;
                iVar13 = iVar13 + -1;
                bVar18 = *pcVar5 == (char)*puVar17;
                pcVar5 = pcVar5 + 1;
                puVar17 = (uint *)((int)puVar17 + 1);
              } while (bVar18);
            }
            if (bVar18) goto LAB_005d4287;
          }
LAB_005d42ab:
          ppppiStack_180 = (int ****)0x5d42b4;
          func_0x00732680();
          ppppiStack_180 = (int ****)0x5d42bf;
          func_0x005c6630();
          ppppiStack_180 = (int ****)0x5d42c8;
          func_0x005132f0();
          pppiStack_c[0x38e] = (int **)pppiStack_138;
          pppiVar7 = pppiStack_c;
LAB_005d42d7:
          ppppiStack_180 = (int ****)0x5d42e0;
          cVar3 = func_0x004a0800();
          if ((cVar3 == '\0') || (pppiStack_138 != (int ***)0xffffffff)) {
            if (iStack_11c == 2) {
LAB_005d4287:
              ppppiStack_180 = (int ****)0x5d4290;
              func_0x005132f0();
              ppppiStack_180 = (int ****)0x5d4299;
              func_0x004abb70();
              return 1000000;
            }
            goto LAB_005d4381;
          }
          ppppiStack_180 = (int ****)0x5d42fa;
          func_0x00733a40();
        }
        else {
          ppppiStack_180 = (int ****)pppiStack_c;
          func_0x006dcc40();
          if (iStack_11c != 1) goto LAB_005d42d7;
          ppppiStack_180 = (int ****)pppiStack_138;
          cVar3 = func_0x004461a0();
          if (cVar3 == '\0') goto LAB_005d42d7;
          ppppiStack_180 = (int ****)0x0;
          cVar3 = func_0x00448a10(pppiVar7[0xaf],pppiStack_138);
          if (cVar3 != '\0') goto LAB_005d4287;
          ppppiStack_180 = (int ****)pppiVar7[0xaf];
          cVar3 = func_0x00448c90();
          if (cVar3 == '\0') {
            func_0x00732160();
          }
          else {
            func_0x007359e0();
          }
        }
        ppppiStack_180 = (int ****)0x5d4305;
        func_0x005c6630();
        ppppiStack_180 = (int ****)0x5d430e;
        func_0x005132f0();
        pppiVar7 = pppiStack_c;
LAB_005d4381:
        ppiStack_15c = (int **)0x0;
        ppppiStack_180 = (int ****)0x5d4392;
        (*(code *)(*pppiVar7)[9])();
        ppppiStack_180 = (int ****)&ppiStack_15c;
        iVar13 = FUN_005e7c20(&stack0xfffffe98);
        if (unaff_EBP != 0) {
          iVar11 = *piStack_14;
          uVar6 = func_0x00561f50(0x111,unaff_EBP,0);
          (**(code **)(iVar11 + 0x5c))(uVar6);
          func_0x00401000();
        }
        func_0x005132f0();
        func_0x004abb70();
        return iVar13;
      }
    }
LAB_005d4407:
    iVar13 = *(int *)(unaff_retaddr + 0x14);
    if (iVar13 != 0) {
      if (iVar13 == -4) {
        if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005d4565;
        bVar18 = false;
      }
      else {
        if (iVar13 == 0) {
          pcVar5 = (char *)0x0;
        }
        else {
          pcVar5 = (char *)(iVar13 + 4);
        }
        iVar13 = 9;
        bVar18 = true;
        pcVar16 = "lb_right";
        do {
          if (iVar13 == 0) break;
          iVar13 = iVar13 + -1;
          bVar18 = *pcVar16 == *pcVar5;
          pcVar16 = pcVar16 + 1;
          pcVar5 = pcVar5 + 1;
        } while (bVar18);
      }
      if (bVar18) {
        pppiStack_178 = (int ***)aiStack_144;
        ppppiStack_17c = (int ****)0x5d447a;
        iVar13 = func_0x005c6780();
        if (iVar13 == 0) {
          if (iStack_118 == 0) {
            ppppiStack_17c = (int ****)0x5d4499;
            cVar3 = func_0x005ec440();
            if (cVar3 != '\0') {
              ppppiStack_17c = (int ****)uStack_134;
              ppppiStack_180 = (int ****)0x5d44af;
              func_0x00451a60();
              ppppiStack_180 = (int ****)0x1;
              func_0x006dc4c0(pppiVar7);
              func_0x004abb70();
              return 0xf4241;
            }
          }
          else {
            if (iStack_118 == 3) {
              ppppiStack_17c = (int ****)0x1;
              ppppiStack_180 = &pppiStack_138;
              func_0x004abba0(pppiVar7[0xb0]);
              func_0x006dc4c0(pppiVar7,1);
              func_0x004abb70();
              return 0xf4241;
            }
            if (((iStack_118 == 6) || (iStack_118 == 7)) && (cStack_130 == '\0')) {
              *(undefined1 *)((int)pppiVar7[0xb0] + 0x166) = 1;
              ppppiStack_17c = (int ****)0xffffffff;
              ppppiStack_180 = (int ****)0x5d454a;
              func_0x004ab9a0();
            }
          }
          ppppiStack_17c = (int ****)0x5d4553;
          func_0x004abb70();
          return 0xf4241;
        }
        goto LAB_005d463d;
      }
    }
LAB_005d4565:
    iVar13 = *(int *)(unaff_retaddr + 0x14);
    if (iVar13 != 0) {
      if (iVar13 == -4) {
        if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005d4790;
        bVar18 = false;
      }
      else {
        if (iVar13 == 0) {
          pcVar5 = (char *)0x0;
        }
        else {
          pcVar5 = (char *)(iVar13 + 4);
        }
        iVar13 = 8;
        bVar18 = true;
        pcVar16 = "lb_left";
        do {
          if (iVar13 == 0) break;
          iVar13 = iVar13 + -1;
          bVar18 = *pcVar16 == *pcVar5;
          pcVar16 = pcVar16 + 1;
          pcVar5 = pcVar5 + 1;
        } while (bVar18);
      }
      if (bVar18) {
        pppiStack_178 = (int ***)aiStack_144;
        ppppiStack_17c = (int ****)0x5d45d1;
        iVar13 = func_0x005c6780();
        if (iVar13 != 0) {
LAB_005d463d:
          ppppiStack_17c = (int ****)0x5d4646;
          func_0x004abb70();
          return iVar13;
        }
        ppppiStack_17c = (int ****)0x5d45e0;
        cVar4 = func_0x004a0800();
        cVar3 = cStack_12f;
        if (cVar4 != '\0') {
          if (((iStack_118 == 6) || (iStack_118 == 7)) &&
             ((cStack_130 != '\0' &&
              (((iStack_118 != 6 && (iStack_118 != 7)) || (cStack_12f != '\x01')))))) {
            *(undefined1 *)((int)pppiVar7[0xb0] + 0x166) = 1;
            ppppiStack_17c = (int ****)0xffffffff;
            ppppiStack_180 = (int ****)0x5d463b;
            iVar13 = func_0x004ab9a0();
            goto LAB_005d463d;
          }
          for (pppiVar14 = (int ***)((int)pppiVar7[0x3ac][200] + (int)pppiVar7[0x3ac][0xbe]);
              -1 < (int)pppiVar14; pppiVar14 = (int ***)((int)pppiVar14 + -1)) {
            ppppiStack_17c = &pppiStack_148;
            ppppiStack_180 = (int ****)pppiVar14;
            func_0x004ae4e0();
            if (cStack_12f < cVar3) {
              ppppiStack_17c = (int ****)0x1;
              ppppiStack_180 = (int ****)0x5d46d0;
              func_0x009d2550();
              pppiVar7[0x3ac][0xc3] = (int *)pppiVar14;
              *(undefined1 *)((int)pppiVar7[0xb0] + 0x166) = 1;
              ppppiStack_180 = (int ****)0x5d46f2;
              func_0x004abb70();
              return 0xf4241;
            }
          }
        }
        if (iStack_118 == 0) {
          ppppiStack_17c = &pppiStack_148;
          ppppiStack_180 = (int ****)pppiVar7;
          iVar13 = func_0x005d2ad0();
          if (iVar13 == 0) {
            ppppiStack_17c = (int ****)uStack_134;
            ppppiStack_180 = (int ****)0x5d46bc;
            func_0x00451a60();
          }
        }
        else if (iStack_118 == 3) {
          ppppiStack_17c = (int ****)0x0;
          ppppiStack_180 = &pppiStack_138;
          func_0x004abba0(pppiVar7[0xb0]);
        }
        else {
          ppiVar9 = pppiVar7[0x3ac];
          if (ppiVar9 != (int **)0x0) {
            pppiVar14 = (int ***)((int)ppiVar9[200] + (int)ppiVar9[0xbe]);
            while( true ) {
              ppppiStack_17c = &pppiStack_148;
              ppppiStack_180 = (int ****)pppiVar14;
              func_0x004ae4e0();
              if (iStack_118 == 0) break;
              pppiVar14 = (int ***)((int)pppiVar14 + -1);
            }
            if (pppiVar7[0x3ac] != (int **)0x0) {
              ppppiStack_17c = (int ****)0x0;
              ppppiStack_180 = (int ****)0x5d4761;
              func_0x009d2550();
              pppiVar7[0x3ac][0xc3] = (int *)pppiVar14;
            }
          }
        }
        ppppiStack_17c = (int ****)0x1;
        ppppiStack_180 = (int ****)pppiVar7;
        func_0x006dc4c0();
        func_0x004abb70();
        return 0xf4241;
      }
    }
LAB_005d4790:
    pppiStack_178 = (int ***)0x5d4799;
    func_0x004abb70();
    return 0;
  }
  if (iVar13 == -4) {
    if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005d4039;
    bVar18 = false;
  }
  else {
    if (iVar13 == 0) {
      pcVar5 = (char *)0x0;
    }
    else {
      pcVar5 = (char *)(iVar13 + 4);
    }
    iVar13 = 0xc;
    bVar18 = true;
    pcVar16 = "lb_preclick";
    do {
      if (iVar13 == 0) break;
      iVar13 = iVar13 + -1;
      bVar18 = *pcVar16 == *pcVar5;
      pcVar16 = pcVar16 + 1;
      pcVar5 = pcVar5 + 1;
    } while (bVar18);
  }
  if (!bVar18) goto LAB_005d4039;
LAB_005d47a8:
  pppiStack_4 = (int ***)pppiVar7[0x353];
  if (pppiStack_4 == (int ***)0x0) {
    return -1;
  }
  uStack_70 = puStack_170;
  uStack_74 = puStack_174;
  uStack_68 = unaff_ESI;
  if ((_DAT_00da0410 & 1) == 0) {
    _DAT_00da0410 = _DAT_00da0410 | 1;
    puStack_78 = &UNK_00cb2720;
    ppiStack_5c = (int **)0x0;
    ppiStack_7c = (int **)0x765d66;
    func_0x00985ff0();
    iVar13 = *(int *)(_DAT_00d67908 + 0x20);
    if (iVar13 != 0) {
      ppiStack_7c = *(int ***)(_DAT_00d67908 + 0x18);
      ppiStack_80 = (int **)0x765d7d;
      iVar11 = func_0x00409df0();
      for (puVar15 = *(undefined4 **)(iVar13 + iVar11 * 4); puVar15 != (undefined4 *)0x0;
          puVar15 = (undefined4 *)*puVar15) {
        ppiStack_7c = (int **)0x765d90;
        cVar3 = func_0x006f9890();
        if (cVar3 != '\0') {
          puVar15 = puVar15 + 1;
          goto LAB_00765d9c;
        }
      }
    }
    puVar15 = (undefined4 *)0x0;
LAB_00765d9c:
    ppiStack_7c = (int **)0x765da5;
    func_0x00401000();
    if (puVar15 == (undefined4 *)0x0) {
      puStack_78 = (undefined *)0x10;
      ppiStack_7c = (int **)0x765dc3;
      func_0x009b9ff0();
      _DAT_00da040c = iStack_58;
    }
    else {
      _DAT_00da040c = puVar15[1];
    }
  }
  ppiStack_7c = *(int ***)(unaff_retaddr + 0xc);
  iStack_58 = (int)pppiStack_4[9][0xb0];
  if (ppiStack_7c == (int **)0xffffffff) {
    return 0xf4241;
  }
  puStack_78 = &uStack_44;
  uStack_44 = 0xff;
  uStack_43 = 0xff;
  uStack_42 = 0xff;
  uStack_41 = 0xff;
  uStack_40 = 0xff;
  uStack_3f = 0xff;
  uStack_3e = 0xff;
  uStack_3d = 0xff;
  uStack_3c = CONCAT22(uStack_3c._2_2_,0xff);
  uStack_38 = 0;
  uStack_34 = 0;
  piStack_14 = (int *)0xa;
  ppiStack_80 = (int **)0x765e3a;
  ppiStack_5c = ppiStack_7c;
  iVar13 = func_0x004ae4e0();
  if (iVar13 != 0) {
    ppiStack_80 = (int **)0x765e49;
    func_0x00401000();
    uStack_3c = 0;
    ppiStack_80 = (int **)0x765e56;
    func_0x00401000();
    return iVar13;
  }
  if (iStack_1c == 4) {
    ppiStack_80 = (int **)&UNK_00cb2878;
    pppiStack_84 = (int ***)0x765e7a;
    piVar8 = (int *)func_0x009ae560();
    if (*piVar8 == 0) {
      pppiStack_84 = (int ***)0x0;
    }
    else {
      pppiStack_84 = (int ***)(*piVar8 + 4);
    }
    ppiStack_80 = (int **)0x0;
    iStack_88 = 0x765e93;
    func_0x009807f0();
    ppiStack_80 = (int **)0x765e9f;
    func_0x00401000();
    uStack_3c = 0;
    ppiStack_80 = (int **)0x765eac;
    func_0x00401000();
    return 1000000;
  }
  if (iStack_1c == 8) {
    iVar13 = *(int *)(unaff_retaddr + 0x14);
    if (iVar13 != 0) {
      if (iVar13 == -4) {
        if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_00765f0f;
        bVar18 = false;
      }
      else {
        if (iVar13 == 0) {
          pcVar5 = (char *)0x0;
        }
        else {
          pcVar5 = (char *)(iVar13 + 4);
        }
        iVar13 = 0xc;
        bVar18 = true;
        pcVar16 = "lb_preclick";
        do {
          if (iVar13 == 0) break;
          iVar13 = iVar13 + -1;
          bVar18 = *pcVar16 == *pcVar5;
          pcVar16 = pcVar16 + 1;
          pcVar5 = pcVar5 + 1;
        } while (bVar18);
      }
      if (!bVar18) goto LAB_00765f0f;
LAB_00765f5a:
      if (uStack_3c == 0) {
        ppiStack_80 = (int **)0x0;
        pppiStack_84 = (int ***)0x0;
        iStack_88 = 0x765f88;
        func_0x00575130();
      }
      else {
        pppiStack_84 = (int ***)(uStack_3c + 4);
        ppiStack_80 = (int **)0x0;
        iStack_88 = 0x765f73;
        func_0x00575130();
      }
      goto LAB_007663ae;
    }
LAB_00765f0f:
    iVar13 = *(int *)(unaff_retaddr + 0x14);
    if (iVar13 != 0) {
      if (iVar13 == -4) {
        if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_00765f8d;
        bVar18 = false;
      }
      else {
        if (iVar13 == 0) {
          pcVar5 = (char *)0x0;
        }
        else {
          pcVar5 = (char *)(iVar13 + 4);
        }
        iVar13 = 0xc;
        bVar18 = true;
        pcVar16 = "lb_activate";
        do {
          if (iVar13 == 0) break;
          iVar13 = iVar13 + -1;
          bVar18 = *pcVar16 == *pcVar5;
          pcVar16 = pcVar16 + 1;
          pcVar5 = pcVar5 + 1;
        } while (bVar18);
      }
      if (bVar18) goto LAB_00765f5a;
    }
  }
LAB_00765f8d:
  iStack_58 = *(int *)(unaff_retaddr + 0x1c);
  iVar13 = *(int *)(unaff_retaddr + 0x18);
  if (*(int **)(unaff_retaddr + 0x24) != (int *)0x0) {
    ppiStack_80 = (int **)0x0;
    pppiStack_84 = &ppiStack_5c;
    iStack_88 = 0x765fad;
    (**(code **)(**(int **)(unaff_retaddr + 0x24) + 0x30))();
    if (DAT_00d678d4 == '\0') {
      iVar13 = iVar13 - (int)ppiStack_5c;
    }
    else {
      iVar13 = iStack_54 - iVar13;
    }
  }
  if (*(char *)(pppiStack_c[9] + 0x37b) != '\0') {
    if (iStack_1c != 1) {
      ppiStack_80 = (int **)0x765fe6;
      cVar3 = func_0x004a0800();
      if (cVar3 == '\0') goto LAB_00766075;
    }
    if (DAT_00d67849 == '\0') {
      cVar3 = '\0';
    }
    else {
      ppiStack_80 = (int **)0x10;
      pppiStack_84 = (int ***)0x766002;
      uVar12 = GetAsyncKeyState();
      cVar3 = (char)((uVar12 & 0xffff) >> 0xf);
    }
    uStack_68 = CONCAT13(iVar13 < 0x20,(uint3)uStack_68);
    if ((iVar13 < 0x20) || (cVar3 != '\0')) {
      ppiStack_80 = (int **)uStack_38;
      pppiStack_84 = (int ***)0x76602b;
      cVar3 = func_0x007617b0();
      if (cVar3 != '\0') {
        ppiStack_5c = (int **)CONCAT31(ppiStack_5c._1_3_,(cVar3 == '\x01') + '\x01');
        ppiStack_80 = ppiStack_5c;
        pppiStack_84 = pppiStack_c;
        iStack_88 = 0x76605f;
        func_0x007663d0();
      }
      pppiStack_c[6] = ppiStack_64;
      if (uStack_68._3_1_ != '\0') goto LAB_007663ae;
    }
  }
LAB_00766075:
  if ((((iStack_1c == 5) || ((iStack_1c != 6 && (iStack_1c == 7)))) && (iStack_1c != 6)) &&
     (iStack_1c != 7)) {
    bVar18 = true;
  }
  else {
    bVar18 = false;
  }
  if ((iStack_1c == 1) || (bVar18)) {
    if ((char)uStack_34 != '\0') goto LAB_007663ae;
    iVar13 = *(int *)(iStack_8 + 0x14);
    if (iVar13 != 0) {
      if (iVar13 == -4) {
        if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_007661f4;
        bVar18 = false;
      }
      else if (iVar13 == 0) {
        iVar13 = 0xd;
        bVar18 = true;
        pcVar5 = "lb_predouble";
        pcVar16 = (char *)0x0;
        do {
          if (iVar13 == 0) break;
          iVar13 = iVar13 + -1;
          bVar18 = *pcVar5 == *pcVar16;
          pcVar5 = pcVar5 + 1;
          pcVar16 = pcVar16 + 1;
        } while (bVar18);
      }
      else {
        iVar11 = 0xd;
        bVar18 = true;
        pcVar5 = "lb_predouble";
        pcVar16 = (char *)(iVar13 + 4);
        do {
          if (iVar11 == 0) break;
          iVar11 = iVar11 + -1;
          bVar18 = *pcVar5 == *pcVar16;
          pcVar5 = pcVar5 + 1;
          pcVar16 = pcVar16 + 1;
        } while (bVar18);
      }
      if (bVar18) {
        ppiStack_80 = (int **)0x7663aa;
        func_0x006db580();
        goto LAB_007663ae;
      }
    }
    goto LAB_007661f4;
  }
  if (iStack_1c == 2) goto LAB_007663ae;
  uStack_68 = uStack_68 & 0xffffff;
  iVar11 = *(int *)(iStack_8 + 0x14);
  if (iVar11 != 0) {
    if (iVar11 == -4) {
      if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_0076612f;
      bVar18 = false;
    }
    else {
      if (iVar11 == 0) {
        pcVar5 = (char *)0x0;
      }
      else {
        pcVar5 = (char *)(iVar11 + 4);
      }
      iVar11 = 0xc;
      bVar18 = true;
      pcVar16 = "lb_activate";
      do {
        if (iVar11 == 0) break;
        iVar11 = iVar11 + -1;
        bVar18 = *pcVar16 == *pcVar5;
        pcVar16 = pcVar16 + 1;
        pcVar5 = pcVar5 + 1;
      } while (bVar18);
    }
    if (bVar18) {
      ppiStack_80 = (int **)0x76610f;
      cVar3 = func_0x004a0800();
      if (cVar3 != '\0') {
        ppiStack_80 = (int **)0x766120;
        func_0x004abb70();
        return 0xf4241;
      }
      goto LAB_007663ae;
    }
  }
LAB_0076612f:
  ppiVar9 = pppiStack_c[0x9c];
  ppiVar1 = pppiStack_c[0x98];
  ppiStack_80 = (int **)0x766150;
  iVar11 = func_0x00761780();
  if ((int)ppiVar9 + iVar11 + -4 < iVar13) {
    uStack_68._0_3_ = (uint3)(ushort)uStack_68;
    if ((int)ppiVar1 + (int)ppiVar9 + iVar11 + 4 <= iVar13) goto LAB_00766167;
  }
  else {
LAB_00766167:
    uStack_68._0_3_ = CONCAT12(1,(ushort)uStack_68);
  }
  ppiStack_80 = (int **)0x766175;
  cVar3 = func_0x004a0800();
  if (((cVar3 == '\0') || (iStack_1c == 6)) || (cVar4 = '\x01', iStack_1c == 7)) {
    cVar4 = uStack_68._2_1_;
  }
  iVar13 = *(int *)(iStack_8 + 0x14);
  if (iVar13 == 0) {
LAB_007661df:
    if (cVar4 != '\0') {
      pppiStack_c[9][0xc1e] = (int *)0xffffffff;
LAB_007661f4:
      ppiStack_80 = (int **)0x7661fd;
      func_0x004abb70();
      return 0xf4241;
    }
  }
  else {
    if (iVar13 == -4) {
      if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_007661df;
      bVar18 = false;
    }
    else {
      if (iVar13 == 0) {
        pcVar5 = (char *)0x0;
      }
      else {
        pcVar5 = (char *)(iVar13 + 4);
      }
      iVar13 = 0xd;
      bVar18 = true;
      pcVar16 = "lb_predouble";
      do {
        if (iVar13 == 0) break;
        iVar13 = iVar13 + -1;
        bVar18 = *pcVar16 == *pcVar5;
        pcVar16 = pcVar16 + 1;
        pcVar5 = pcVar5 + 1;
      } while (bVar18);
    }
    if (!bVar18) goto LAB_007661df;
  }
  if (iStack_1c == 0) {
    pppiStack_84 = (int ***)pppiStack_c[9];
    ppiStack_80 = (int **)auStack_4c;
    iStack_88 = 0x766226;
    iVar13 = func_0x005d2ad0();
    if (iVar13 == 0xf4242) goto LAB_007663ae;
LAB_00766231:
    if ((cVar3 == '\0') || (uStack_34._1_1_ != '\x01')) {
      ppiStack_80 = (int **)0xffffffff;
      pppiStack_84 = (int ***)0x76624b;
      func_0x004ab9a0();
      uStack_68 = CONCAT13(1,(uint3)uStack_68);
      if (cVar3 != '\0') goto LAB_007663ae;
    }
  }
  else {
    if (iStack_1c != 3) goto LAB_00766231;
    ppiStack_80 = (int **)0xffffffff;
    pppiStack_84 = (int ***)&uStack_3c;
    iStack_88 = iStack_60;
    ppiStack_8c = (int **)0x7662cd;
    func_0x004abba0();
  }
  ppiStack_80 = (int **)0x1;
  pppiStack_84 = (int ***)0x0;
  *(undefined1 *)(iStack_60 + 0x166) = 1;
  ppiStack_8c = pppiStack_c[9];
  iStack_88 = 0;
  uStack_90 = 0x766276;
  func_0x0065b840();
  if (uStack_68._3_1_ != '\0') {
LAB_007663ae:
    ppiStack_80 = (int **)0x7663b3;
    func_0x004abb70();
    return 1000000;
  }
  if (((iStack_1c == 0) || (iStack_1c == 3)) && (iVar13 = *(int *)(iStack_8 + 0x14), iVar13 != 0)) {
    if (iVar13 == -4) {
      if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_00766306;
      bVar18 = false;
    }
    else if (iVar13 == 0) {
      iVar13 = 0xc;
      bVar18 = true;
      pcVar5 = "lb_preclick";
      pcVar16 = (char *)0x0;
      do {
        if (iVar13 == 0) break;
        iVar13 = iVar13 + -1;
        bVar18 = *pcVar5 == *pcVar16;
        pcVar5 = pcVar5 + 1;
        pcVar16 = pcVar16 + 1;
      } while (bVar18);
    }
    else {
      iVar11 = 0xc;
      bVar18 = true;
      pcVar5 = "lb_preclick";
      pcVar16 = (char *)(iVar13 + 4);
      do {
        if (iVar11 == 0) break;
        iVar11 = iVar11 + -1;
        bVar18 = *pcVar5 == *pcVar16;
        pcVar5 = pcVar5 + 1;
        pcVar16 = pcVar16 + 1;
      } while (bVar18);
    }
    if (bVar18) {
      bVar2 = 1;
      goto LAB_00766308;
    }
  }
LAB_00766306:
  bVar2 = 0;
LAB_00766308:
  ppiStack_80 = (int **)0x766311;
  func_0x004abb70();
  return bVar2 + 1000000;
}


