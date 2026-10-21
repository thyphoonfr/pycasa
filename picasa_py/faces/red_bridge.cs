// Ref: picasa3.exe @ 0x006CC9E0..0x006CD9B0 (CRedFaceDetector)
// Ref: picasa3.exe @ 0x0047A690..0x0047AE7E (Face box & landmark post-processing)
// Ref: Red.dll @ 0x10001930 (REDENTRY) & vtable 0x101AADC4 (vt[0..31])
// Ghidra project: ghidra/picasa3.gpr
using System;
using System.IO;
using System.Runtime.InteropServices;

[StructLayout(LayoutKind.Sequential, Pack = 4)]
public struct RedCtx24 {
    public uint w0, w1, w2, w3, w4, w5;
}

[StructLayout(LayoutKind.Sequential, Pack = 4)]
public unsafe struct RedFace104 {
    public fixed float f[26];
}

[StructLayout(LayoutKind.Sequential, Pack = 4)]
public struct RedTemplateOut {
    public uint id;
    public uint size;
    public IntPtr data;
}

public unsafe class RedBridge {
    [DllImport("kernel32.dll", CharSet = CharSet.Ansi, SetLastError = true)]
    static extern IntPtr LoadLibraryA(string lpFileName);

    [DllImport("kernel32.dll", CharSet = CharSet.Ansi, SetLastError = true)]
    static extern IntPtr GetProcAddress(IntPtr hModule, string lpProcName);

    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    delegate int RedEntryDel(int version, out IntPtr ifacePtr);

    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    delegate int Vt0_Init(out RedCtx24 ctx, [MarshalAs(UnmanagedType.LPStr)] string cfgPath);

    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    delegate int Vt1_Destroy(RedCtx24 ctx);

    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    delegate int Vt4_SetParam(uint w0, [MarshalAs(UnmanagedType.LPStr)] string cmd, float* vals);

    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    delegate int Vt14_DetectAndExtractAll(
        RedCtx24 ctx,
        IntPtr grayPixels,
        int width,
        int height,
        RedFace104* outFaces,
        int maxCount,
        out int outCount,
        RedTemplateOut* outTpls,
        float minConf
    );

    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    delegate int Vt29_FreeTemplate(ref RedTemplateOut tpl);

    static bool ReadExact(Stream s, byte[] buf, int count) {
        int offset = 0;
        while (offset < count) {
            int n = s.Read(buf, offset, count - offset);
            if (n <= 0) return false;
            offset += n;
        }
        return true;
    }

    public static int Main(string[] args) {
        if (args.Length < 2) return 1;
        string dllPath = args[0];
        string cfgPath = args[1];

        Stream stdin = Console.OpenStandardInput();
        Stream stdout = Console.OpenStandardOutput();
        BinaryWriter bw = new BinaryWriter(stdout);

        IntPtr hMod = LoadLibraryA(dllPath);
        if (hMod == IntPtr.Zero) {
            bw.Write((int)0);
            bw.Flush();
            return 2;
        }
        IntPtr pEntry = GetProcAddress(hMod, "REDENTRY");
        if (pEntry == IntPtr.Zero) {
            bw.Write((int)0);
            bw.Flush();
            return 3;
        }

        var redEntry = (RedEntryDel)Marshal.GetDelegateForFunctionPointer(pEntry, typeof(RedEntryDel));
        IntPtr ifaceObj;
        if (redEntry(1, out ifaceObj) != 0 || ifaceObj == IntPtr.Zero) {
            bw.Write((int)0);
            bw.Flush();
            return 4;
        }

        IntPtr vtable = *(IntPtr*)ifaceObj;
        var vt0 = (Vt0_Init)Marshal.GetDelegateForFunctionPointer(*((IntPtr*)vtable + 0), typeof(Vt0_Init));
        var vt1 = (Vt1_Destroy)Marshal.GetDelegateForFunctionPointer(*((IntPtr*)vtable + 1), typeof(Vt1_Destroy));
        var vt4 = (Vt4_SetParam)Marshal.GetDelegateForFunctionPointer(*((IntPtr*)vtable + 4), typeof(Vt4_SetParam));
        var vt14 = (Vt14_DetectAndExtractAll)Marshal.GetDelegateForFunctionPointer(*((IntPtr*)vtable + 14), typeof(Vt14_DetectAndExtractAll));
        var vt29 = (Vt29_FreeTemplate)Marshal.GetDelegateForFunctionPointer(*((IntPtr*)vtable + 29), typeof(Vt29_FreeTemplate));

        RedCtx24 ctx;
        if (vt0(out ctx, cfgPath) != 0) {
            bw.Write((int)0);
            bw.Flush();
            return 5;
        }

        // Ref: picasa3.exe @ 0x006CCDEF..0x006CCE0C -> vt[4]("set range", {20.0f, 10000.0f}) & vt[5]("set roll", {45.0f})
        float* rangeVals = stackalloc float[2];
        rangeVals[0] = 20.0f;
        rangeVals[1] = 10000.0f;
        vt4(ctx.w0, "set range", rangeVals);

        float* rollVal = stackalloc float[1];
        rollVal[0] = 45.0f;
        vt4(ctx.w0, "set roll", rollVal);

        // Signal ready (1)
        bw.Write((int)1);
        bw.Flush();

        const int MAX_FACES = 1024;
        RedFace104[] faces = new RedFace104[MAX_FACES];
        RedTemplateOut[] tpls = new RedTemplateOut[MAX_FACES];
        byte[] hdrBuf = new byte[12];
        byte[] imgBuf = null;

        while (true) {
            if (!ReadExact(stdin, hdrBuf, 12)) break;
            int width = BitConverter.ToInt32(hdrBuf, 0);
            int height = BitConverter.ToInt32(hdrBuf, 4);
            float minConfidence = BitConverter.ToSingle(hdrBuf, 8);
            if (width <= 0 || height <= 0) break;

            int numPixels = width * height;
            if (imgBuf == null || imgBuf.Length < numPixels) {
                imgBuf = new byte[numPixels];
            }
            if (!ReadExact(stdin, imgBuf, numPixels)) break;

            int count = 0;
            int rc;
            fixed (byte* pGray = imgBuf)
            fixed (RedFace104* pFaces = faces)
            fixed (RedTemplateOut* pTpls = tpls) {
                // Ref: picasa3.exe @ 0x006CD648 -> calls vt[14] with 0.2f
                rc = vt14(ctx, (IntPtr)pGray, width, height, pFaces, MAX_FACES, out count, pTpls, 0.2f);
            }

            if (rc != 0 || count <= 0) {
                bw.Write((int)0);
                bw.Flush();
                continue;
            }

            // Filter & post-process exactly as picasa3.exe @ 0x0047A778..0x0047AE64
            // First count how many pass minConfidence (0x0047A792: esi[+0x2c] >= ebp[+0x08])
            int validCount = 0;
            for (int i = 0; i < count; i++) {
                fixed (RedFace104* pf = &faces[i]) {
                    float conf = pf->f[11]; // +0x2C
                    if (minConfidence > 0.0f && conf < minConfidence) {
                        continue;
                    }
                    validCount++;
                }
            }

            bw.Write((int)validCount);

            for (int i = 0; i < count; i++) {
                fixed (RedFace104* pf = &faces[i]) {
                    float rawConf = pf->f[11]; // +0x2C
                    if (minConfidence > 0.0f && rawConf < minConfidence) {
                        if (tpls[i].data != IntPtr.Zero) {
                            vt29(ref tpls[i]);
                        }
                        continue;
                    }

                    // Raw integer box from 0x006CD8AD..0x006CD8E6
                    int xmin = (int)pf->f[0]; // +0x00
                    int xmax = (int)pf->f[1]; // +0x04
                    int ymin = (int)pf->f[2]; // +0x08
                    int ymax = (int)pf->f[3]; // +0x0C

                    float roll = pf->f[17];   // +0x44 -> esi[+0x34]
                    float pan  = pf->f[18];   // +0x48 -> esi[+0x30]
                    float unk38 = pf->f[19];  // +0x4C -> esi[+0x38]
                    float lx = pf->f[20];     // +0x50 -> esi[+0x3C]
                    float ly = pf->f[21];     // +0x54 -> esi[+0x40]
                    float rx = pf->f[22];     // +0x58 -> esi[+0x44]
                    float ry = pf->f[23];     // +0x5C -> esi[+0x48]
                    float ex = pf->f[24];     // +0x60 -> esi[+0x4C]
                    float ey = pf->f[25];     // +0x64 -> esi[+0x50]

                    float absPan = Math.Abs(pan);

                    // Ref: picasa3.exe @ 0x0047AA88..0x0047AD78
                    if (absPan >= 60.0f) {
                        // Profile branch (0x0047AA9D..0x0047ABFE)
                        if (ex != 0.0f && ey != 0.0f) {
                            float midX = 0.5f * (lx + rx);
                            float midY = 0.5f * (ly + ry);
                            float dx = midX - ex;
                            float dy = midY - ey;
                            float d = (float)(Math.Sqrt(dx * dx + dy * dy) / 6.0);
                            float fxmin = Math.Max(0.0f, midX - 10.0f * d);
                            float fxmax = Math.Min((float)(width - 1), midX + 10.0f * d);
                            float fymin = Math.Max(0.0f, midY - 12.0f * d);
                            float fymax = Math.Min((float)(height - 1), midY + 12.0f * d);
                            xmin = (int)fxmin;
                            ymin = (int)fymin;
                            xmax = (int)fxmax;
                            ymax = (int)fymax;
                        }
                    } else {
                        // Frontal / 3-4 branch (0x0047AC05..0x0047AD78)
                        if (lx != 0.0f && rx != 0.0f) {
                            float midY = 0.5f * (ly + ry);
                            float midX = 0.5f * (lx + rx);
                            float dx = lx - rx;
                            float dy = ly - ry;
                            float d = (float)(Math.Sqrt(dx * dx + dy * dy) / 22.0);
                            float fxmin = Math.Max(0.0f, midX - 40.0f * d);
                            float fxmax = Math.Min((float)(width - 1), midX + 40.0f * d);
                            float fymin = Math.Max(0.0f, midY - 46.0f * d);
                            float fymax = Math.Min((float)(height - 1), midY + 50.0f * d);
                            xmin = (int)fxmin;
                            ymin = (int)fymin;
                            xmax = (int)fxmax;
                            ymax = (int)fymax;
                        }
                    }

                    // Normalized float coordinates (0x0047AD84..0x0047ADD8)
                    float normLeft   = (float)xmin / (float)width;
                    float normTop    = (float)ymin / (float)height;
                    float normRight  = (float)xmax / (float)width;
                    float normBottom = (float)ymax / (float)height;

                    // Yaw penalty on confidence if abs(pan) > 20.0 (0x0047AE0B..0x0047AE52)
                    float finalConf = rawConf;
                    if (absPan > 20.0f) {
                        float clampedPan = Math.Min(54.9f, absPan);
                        float factor = (float)((55.0 - clampedPan) / 54.9);
                        finalConf *= factor;
                    }

                    bw.Write(normLeft);
                    bw.Write(normTop);
                    bw.Write(normRight);
                    bw.Write(normBottom);
                    bw.Write(finalConf);
                    bw.Write(pan);
                    bw.Write(roll);

                    int tplSize = (tpls[i].data != IntPtr.Zero && tpls[i].size > 0) ? (int)tpls[i].size : 0;
                    bw.Write(tplSize);
                    if (tplSize > 0) {
                        byte[] tplBytes = new byte[tplSize];
                        Marshal.Copy(tpls[i].data, tplBytes, 0, tplSize);
                        bw.Write(tplBytes);
                    }
                    if (tpls[i].data != IntPtr.Zero) {
                        vt29(ref tpls[i]);
                    }
                }
            }
            bw.Flush();
        }

        vt1(ctx);
        return 0;
    }
}
