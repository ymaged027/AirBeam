using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text;
using System.Windows.Forms;

[assembly: AssemblyTitle("AirBeam")]
[assembly: AssemblyDescription("AirBeam v5.3 - Ultra-Speed Wireless Transfer")]
[assembly: AssemblyCompany("AirBeam Wireless")]
[assembly: AssemblyProduct("AirBeam")]
[assembly: AssemblyCopyright("Copyright © 2026 AirBeam")]
[assembly: AssemblyVersion("5.3.0.0")]
[assembly: AssemblyFileVersion("5.3.0.0")]

namespace AirBeamLauncher
{
    static class Program
    {
        [STAThread]
        static void Main(string[] args)
        {
            try
            {
                string appDir = AppDomain.CurrentDomain.BaseDirectory;
                string scriptPath = Path.Combine(appDir, "desktop-sender", "sender.py");
                string distExe = Path.Combine(appDir, "dist", "AirBeam", "AirBeam.exe");

                string pythonExe = FindPythonExecutable();

                if (File.Exists(scriptPath) && !string.IsNullOrEmpty(pythonExe))
                {
                    StringBuilder argBuilder = new StringBuilder();
                    argBuilder.AppendFormat("\"{0}\"", scriptPath);

                    if (args != null && args.Length > 0)
                    {
                        foreach (string arg in args)
                        {
                            argBuilder.Append(" ");
                            argBuilder.AppendFormat("\"{0}\"", arg.Replace("\"", "\\\""));
                        }
                    }

                    bool isPythonW = pythonExe.EndsWith("pythonw.exe", StringComparison.OrdinalIgnoreCase) ||
                                     pythonExe.EndsWith("pyw.exe", StringComparison.OrdinalIgnoreCase);

                    ProcessStartInfo psi = new ProcessStartInfo
                    {
                        FileName = pythonExe,
                        Arguments = argBuilder.ToString(),
                        WorkingDirectory = appDir,
                        UseShellExecute = isPythonW,
                        CreateNoWindow = !isPythonW,
                        WindowStyle = ProcessWindowStyle.Normal
                    };

                    Process.Start(psi);
                    return;
                }

                if (File.Exists(distExe))
                {
                    StringBuilder argBuilder = new StringBuilder();
                    if (args != null && args.Length > 0)
                    {
                        foreach (string arg in args)
                        {
                            if (argBuilder.Length > 0) argBuilder.Append(" ");
                            argBuilder.AppendFormat("\"{0}\"", arg.Replace("\"", "\\\""));
                        }
                    }

                    ProcessStartInfo psi = new ProcessStartInfo
                    {
                        FileName = distExe,
                        Arguments = argBuilder.ToString(),
                        WorkingDirectory = Path.GetDirectoryName(distExe),
                        UseShellExecute = false
                    };

                    Process.Start(psi);
                    return;
                }

                MessageBox.Show(
                    "AirBeam could not find a suitable Python runtime (pythonw.exe) or standalone executable.\n\nPlease verify that Python 3.10+ is installed.",
                    "AirBeam - Runtime Not Found",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    "Error launching AirBeam: " + ex.Message,
                    "AirBeam Launch Error",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
            }
        }

        static string FindPythonExecutable()
        {
            string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);

            // Specific known Python 3.14 path on this machine
            string py314 = Path.Combine(localAppData, "Python", "pythoncore-3.14-64", "pythonw.exe");
            if (File.Exists(py314)) return py314;

            string py314Cli = Path.Combine(localAppData, "Python", "pythoncore-3.14-64", "python.exe");
            if (File.Exists(py314Cli)) return py314Cli;

            // Search LocalPrograms
            string programsDir = Path.Combine(localAppData, "Programs", "Python");
            if (Directory.Exists(programsDir))
            {
                foreach (string dir in Directory.GetDirectories(programsDir, "Python*"))
                {
                    string candidate = Path.Combine(dir, "pythonw.exe");
                    if (File.Exists(candidate)) return candidate;
                }
            }

            // Check PATH entries
            string pathEnv = Environment.GetEnvironmentVariable("PATH") ?? "";
            string[] searchFiles = new string[] { "pythonw.exe", "pyw.exe", "python.exe", "py.exe" };

            foreach (string entry in pathEnv.Split(';'))
            {
                string trimmed = entry.Trim().Trim('"');
                if (string.IsNullOrEmpty(trimmed)) continue;

                foreach (string file in searchFiles)
                {
                    try
                    {
                        string candidate = Path.Combine(trimmed, file);
                        if (File.Exists(candidate)) return candidate;
                    }
                    catch { }
                }
            }

            // Check system root drives
            string[] sysRoots = new string[] {
                @"C:\Python314", @"C:\Python313", @"C:\Python312", @"C:\Python311",
                @"C:\Program Files\Python314", @"C:\Program Files\Python313", @"C:\Program Files\Python312"
            };
            foreach (string root in sysRoots)
            {
                string candidate = Path.Combine(root, "pythonw.exe");
                if (File.Exists(candidate)) return candidate;
            }

            return null;
        }
    }
}
