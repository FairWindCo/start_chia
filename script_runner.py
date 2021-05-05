import subprocess
import sys
import time

chia_path = r'~\AppData\Local\chia-blockchain\app-1.1.2\resources\app.asar.unpacked\daemon\chia.exe'
temp_dir = r'd:\TEMP_FARM'
farm_dir = r'D:\FARM'
farmer_pub_key = '969970d56c45dcfc41f8d0aa2f3d4f5f2f3fc02bde57ce58c5dd0823e0f38fc61814b1d5f273a8ea198ef4f59755cce8'
pool_pub_key = 'ae0e79d9ea4a7493e2796916d0dde6b20bac00fd7314d3379776939c8d15e151d28506a7c14f914400bded7123f0346d'
fingerprint = 2299237634


if __name__ == "__main__":

    cmd = f"{chia_path} plots create -k 32 -b 8000 -r 2 -t {temp_dir} -d {farm_dir} -f {farmer_pub_key} -p {pool_pub_key} -a {fingerprint}"
    print(cmd)
    start_time = time.time()
    p = subprocess.Popen(['powershell.exe', cmd], stdout=sys.stdout)
    p.wait()
    print(f"Create plot use {time.time() - start_time}s")