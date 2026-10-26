using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

public class LoopbackInstaller
{
    private const int MAX_CLASS_NAME_LEN = 32;
    private const int DICD_GENERATE_ID = 0x00000001;
    private const int SPDRP_HARDWAREID = 0x00000001;
    private const int DIF_REGISTERDEVICE = 0x00000019;
    private const int DIF_REMOVE = 0x00000002;
    private const uint INSTALLFLAG_FORCE = 0x00000001;

    [StructLayout(LayoutKind.Sequential)]
    public struct SP_DEVINFO_DATA
    {
        public uint cbSize;
        public Guid ClassGuid;
        public uint DevInst;
        public IntPtr Reserved;
    }

    [DllImport("setupapi.dll", SetLastError = true, CharSet = CharSet.Unicode, EntryPoint = "SetupDiGetINFClassW")]
    public static extern bool SetupDiGetINFClass(
        string infName,
        ref Guid classGuid,
        StringBuilder className,
        int classNameSize,
        out int requiredSize
    );

    [DllImport("setupapi.dll", SetLastError = true)]
    public static extern IntPtr SetupDiCreateDeviceInfoList(
        ref Guid classGuid, 
        IntPtr hwndParent
    );

    [DllImport("setupapi.dll", SetLastError = true, CharSet = CharSet.Unicode, EntryPoint = "SetupDiCreateDeviceInfoW")]
    public static extern bool SetupDiCreateDeviceInfo(
        IntPtr deviceInfoSet,
        string deviceName,
        ref Guid classGuid,
        string deviceDescription,
        IntPtr hwndParent,
        uint creationFlags,
        ref SP_DEVINFO_DATA deviceInfoData
    );

    [DllImport("setupapi.dll", SetLastError = true, CharSet = CharSet.Unicode, EntryPoint = "SetupDiSetDeviceRegistryPropertyW")]
    public static extern bool SetupDiSetDeviceRegistryProperty(
        IntPtr deviceInfoSet,
        ref SP_DEVINFO_DATA deviceInfoData,
        uint property,
        byte[] propertyBuffer,
        uint propertyBufferSize
    );

    [DllImport("setupapi.dll", SetLastError = true)]
    public static extern bool SetupDiCallClassInstaller(
        uint installFunction,
        IntPtr deviceInfoSet,
        ref SP_DEVINFO_DATA deviceInfoData
    );

    [DllImport("newdev.dll", SetLastError = true, CharSet = CharSet.Unicode, EntryPoint = "UpdateDriverForPlugAndPlayDevicesW")]
    public static extern bool UpdateDriverForPlugAndPlayDevices(
        IntPtr hwndParent,
        string hardwareId,
        string fullInfPath,
        uint installFlags,
        out bool pfRebootRequired
    );

    [DllImport("setupapi.dll", SetLastError = true)]
    public static extern bool SetupDiDestroyDeviceInfoList(IntPtr deviceInfoSet);

    private static void Log(string message)
    {
        try
        {
            string logPath = Path.Combine(Path.GetTempPath(), "airbeam_loopback_install.log");
            File.AppendAllText(logPath, "[" + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "] " + message + Environment.NewLine);
        }
        catch {}
    }

    public static int Main(string[] args)
    {
        Log("=== AirBeam Loopback Installer Started ===");
        string infPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Inf", "netloop.inf");
        string hardwareId = "*MSLOOP";

        if (!File.Exists(infPath))
        {
            Log("Error: netloop.inf not found at: " + infPath);
            return 10;
        }

        StringBuilder className = new StringBuilder(MAX_CLASS_NAME_LEN);
        Guid classGuid = Guid.Empty;
        int reqSize = 0;

        if (!SetupDiGetINFClass(infPath, ref classGuid, className, MAX_CLASS_NAME_LEN, out reqSize))
        {
            int err = Marshal.GetLastWin32Error();
            Log("SetupDiGetINFClass failed with error: " + err);
            return 1;
        }
        Log("Found INF Class: " + className.ToString() + ", GUID: " + classGuid.ToString());

        IntPtr deviceInfoSet = SetupDiCreateDeviceInfoList(ref classGuid, IntPtr.Zero);
        if (deviceInfoSet == IntPtr.Zero || deviceInfoSet.ToInt64() == -1)
        {
            int err = Marshal.GetLastWin32Error();
            Log("SetupDiCreateDeviceInfoList failed with error: " + err);
            return 2;
        }

        try
        {
            SP_DEVINFO_DATA deviceInfoData = new SP_DEVINFO_DATA();
            deviceInfoData.cbSize = (uint)Marshal.SizeOf(deviceInfoData);

            if (!SetupDiCreateDeviceInfo(deviceInfoSet, className.ToString(), ref classGuid, null, IntPtr.Zero, DICD_GENERATE_ID, ref deviceInfoData))
            {
                int err = Marshal.GetLastWin32Error();
                Log("SetupDiCreateDeviceInfo failed with error: " + err);
                return 3;
            }
            Log("SetupDiCreateDeviceInfo succeeded");

            byte[] hwIdBytes = Encoding.Unicode.GetBytes(hardwareId + "\0\0");
            if (!SetupDiSetDeviceRegistryProperty(deviceInfoSet, ref deviceInfoData, SPDRP_HARDWAREID, hwIdBytes, (uint)hwIdBytes.Length))
            {
                int err = Marshal.GetLastWin32Error();
                Log("SetupDiSetDeviceRegistryProperty failed with error: " + err);
                return 4;
            }
            Log("SetupDiSetDeviceRegistryProperty (*MSLOOP) succeeded");

            if (!SetupDiCallClassInstaller(DIF_REGISTERDEVICE, deviceInfoSet, ref deviceInfoData))
            {
                int err = Marshal.GetLastWin32Error();
                Log("SetupDiCallClassInstaller(DIF_REGISTERDEVICE) failed with error: " + err);
                return 5;
            }
            Log("DIF_REGISTERDEVICE succeeded");

            bool rebootRequired;
            if (!UpdateDriverForPlugAndPlayDevices(IntPtr.Zero, hardwareId, infPath, INSTALLFLAG_FORCE, out rebootRequired))
            {
                int err = Marshal.GetLastWin32Error();
                Log("UpdateDriverForPlugAndPlayDevices failed with error: " + err);
                SetupDiCallClassInstaller(DIF_REMOVE, deviceInfoSet, ref deviceInfoData);
                return 6;
            }
            Log("UpdateDriverForPlugAndPlayDevices succeeded! Reboot required: " + rebootRequired);

            // Post-install configuration: Rename to Loopback and assign dummy IP
            try
            {
                string psScript = "$a = $null; for($i=0; $i -lt 12; $i++){ Start-Sleep -Milliseconds 500; $a = Get-NetAdapter -ErrorAction SilentlyContinue | Where-Object { $_.InterfaceDescription -like '*Loopback*' -or $_.Name -like '*Loopback*' } | Select-Object -First 1; if ($a) { break } }; if ($a) { try { Rename-NetAdapter -Name $a.Name -NewName 'Loopback' -ErrorAction SilentlyContinue } catch {}; try { New-NetIPAddress -InterfaceAlias 'Loopback' -IPAddress '192.168.100.10' -PrefixLength 24 -DefaultGateway '192.168.100.1' -ErrorAction SilentlyContinue } catch {} }";
                ProcessStartInfo psi = new ProcessStartInfo("powershell.exe", "-NoProfile -ExecutionPolicy Bypass -Command \"" + psScript + "\"")
                {
                    CreateNoWindow = true,
                    UseShellExecute = false
                };
                Process p = Process.Start(psi);
                if (p != null) p.WaitForExit(6000);
                Log("Post-install adapter configuration completed.");
            }
            catch (Exception ex)
            {
                Log("Post-install configuration notice: " + ex.Message);
            }

            Log("=== AirBeam Loopback Installer Completed Successfully ===");
            return 0;
        }
        catch (Exception ex)
        {
            Log("Exception during installation: " + ex.ToString());
            return 99;
        }
        finally
        {
            SetupDiDestroyDeviceInfoList(deviceInfoSet);
        }
    }
}
