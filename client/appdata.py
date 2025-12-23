import os
import vdf
import time
import zlib

def get_appdata(app_name: str, exe_path: str, icon:str='') -> dict:
    key=exe_path.lower()
    appid = zlib.crc32(key.encode('utf-8')) & 0xFFFFFFFF
    # long_appid = (appid << 32) | 0x02000000
    # print(f"Long AppID: {long_appid}")
    return {
        'appid': appid,#0,
        'AppName': app_name,
        'Exe': exe_path,
        'StartDir': os.path.split(exe_path)[0]+"\\",
        'icon': icon,
        'ShortcutPath': '',
        'LaunchOptions': '', 
        'IsHidden': 0, 
        'AllowDesktopConfig': 1, 
        'AllowOverlay': 1, 
        'OpenVR': 0, 
        'Devkit': 0, 
        'DevkitGameID': '', 
        'DevkitOverrideAppID': 0, 
        'LastPlayTime': 1765560286, 
        'FlatpakAppID': '', 
        'sortas': '', 
        'tags': {}
    }

def read_binaryVDF(path: str) -> dict:
    with open(path,"rb") as f:
        data=vdf.binary_loads(f.read())
    return data

def write_binaryVDF(data: dict, path: str, backup=True):
    if backup:
        os.rename(path,path+"_"+str(time.time())+".bk")
    f=open(path,"wb")
    try:
        vdf.binary_dump(data,f)
        f.close()
        return True
    except:
        f.close()
        return False

def get_grid_id(appid: int) -> int:
    return(appid & 0xFFFFFFFF)

