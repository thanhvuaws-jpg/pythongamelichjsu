"""Đưa game lên VPS, vào thư mục RIÊNG /opt/sukydieutra (không đụng gì tới đồ án trên cùng máy).

    python trien_khai_vps/day_len_vps.py              đóng gói mã, gửi lên, build và chạy lại
    python trien_khai_vps/day_len_vps.py --trang-thai  container, /health, kết nối tunnel
    python trien_khai_vps/day_len_vps.py --nhat-ky app|tunnel|db
    python trien_khai_vps/day_len_vps.py --dung        tắt game (giữ dữ liệu)
    python trien_khai_vps/day_len_vps.py --go-sach --that   GỠ HẲN: xóa container, CSDL, ảnh, thư mục

Cần (đều nằm cạnh tệp này, KHÔNG đưa lên git — xem .gitignore):
  vps.json      {"dia_chi": ..., "nguoi_dung": "root", "khoa_ssh": "~/.ssh/...", "ten_mien": "vtkt.online"}
  dan_token_vao_day.txt   dán lệnh "docker run ... --token ..." (hoặc chỉ token) của tunnel Cloudflare
Lần đầu chạy, script tự sinh .env (mật khẩu CSDL + token) và app.env (khóa JWT, tài khoản quản trị).
Mật khẩu quản trị nằm trong app.env (ADMIN_PASSWORD) — script không in ra màn hình.
"""
import io
import json
import os
import re
import secrets
import string
import subprocess
import sys
import tarfile
import time
from pathlib import Path

DAY = Path(__file__).resolve().parent
GOC = DAY.parent
THU_MUC_VPS = '/opt/sukydieutra'
DUA_LEN = ['Dockerfile', '.dockerignore', 'backend', 'game', 'shared', 'tools', 'web']
BO_QUA = {'__pycache__', '.pytest_cache', '.ruff_cache', '.hypothesis', '.save', 'tests', '.media',
          '.env', 'sukydieutra_backend.egg-info'}


def cau_hinh():
    tep = DAY / 'vps.json'
    if not tep.exists():
        sys.exit(f'Thieu {tep} (dia_chi, nguoi_dung, khoa_ssh, ten_mien)')
    return json.loads(tep.read_text(encoding='utf-8'))


CH = cau_hinh()
DICH = f"{CH.get('nguoi_dung', 'root')}@{CH['dia_chi']}"
SSH = ['-i', os.path.expanduser(CH['khoa_ssh']), '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20',
       '-o', 'StrictHostKeyChecking=accept-new']


def che(chu):
    return chu.replace(CH['dia_chi'], '<ip VPS>')


def ssh(lenh, in_ra=True, dau_vao=None):
    r = subprocess.run(['ssh', *SSH, DICH, lenh], input=dau_vao, capture_output=True)
    out = che((r.stdout + r.stderr).decode('utf-8', 'replace'))
    if in_ra and out.strip():
        print(out.rstrip())
    return r.returncode, out


def gui_tep(noi_dung: bytes, duong_dan_vps: str, quyen='600'):
    ma, _ = ssh(f"umask 077 && cat > '{duong_dan_vps}' && chmod {quyen} '{duong_dan_vps}'", in_ra=False,
                dau_vao=noi_dung)
    if ma:
        sys.exit(f'Khong gui duoc {duong_dan_vps}')


def doc_env(tep: Path) -> dict:
    if not tep.exists():
        return {}
    ra = {}
    for dong in tep.read_text(encoding='utf-8').splitlines():
        if '=' in dong and not dong.lstrip().startswith('#'):
            k, v = dong.split('=', 1)
            ra[k.strip()] = v.strip()
    return ra


def ghi_env(tep: Path, d: dict, dau=''):
    tep.write_text(dau + ''.join(f'{k}={v}\n' for k, v in d.items()), encoding='utf-8')


def ngau_nhien(n):
    bang = string.ascii_letters + string.digits
    return ''.join(secrets.choice(bang) for _ in range(n))


def chuan_bi_bien():
    """.env (compose) và app.env (máy chủ game): sinh lần đầu, giữ nguyên các lần sau."""
    env = doc_env(DAY / '.env')
    env.setdefault('POSTGRES_PASSWORD', ngau_nhien(32))
    dan = (DAY / 'dan_token_vao_day.txt').read_text(encoding='utf-8').strip() \
        if (DAY / 'dan_token_vao_day.txt').exists() else ''
    if dan:
        m = re.search(r'--token\s+(\S+)', dan)
        token = m.group(1) if m else dan.split()[-1]
        if not re.fullmatch(r'[A-Za-z0-9_\-=.]{40,}', token):
            sys.exit('Noi dung dan_token_vao_day.txt khong giong token tunnel (kiem tra lai lenh da dan)')
        env['TUNNEL_TOKEN'] = token
    if not env.get('TUNNEL_TOKEN'):
        sys.exit('Chua co token tunnel: dan lenh "docker run ... --token ..." vao trien_khai_vps/dan_token_vao_day.txt')
    ghi_env(DAY / '.env', env, '# Bien cho docker compose tren VPS. KHONG dua len git.\n')

    ten = CH['ten_mien']
    app = doc_env(DAY / 'app.env')
    mac_dinh = {
        'ENVIRONMENT': 'production',
        'JWT_SECRET': ngau_nhien(48),
        'WEB_BASE_URL': f'https://game.{ten}',
        'CORS_ORIGINS': f'https://game.{ten},https://admin.{ten}',
        'ADMIN_HOST': f'admin.{ten}',
        'SKIP_EMAIL_VERIFICATION': 'true',
        'EMAIL_BACKEND': 'console',
        'ADMIN_EMAIL': f'admin@{ten}',
        'ADMIN_PASSWORD': ngau_nhien(16),
    }
    for k, v in mac_dinh.items():
        app.setdefault(k, v)
    ghi_env(DAY / 'app.env', app, '# Cau hinh may chu game tren VPS. KHONG dua len git.\n'
                                  '# Dang nhap quan tri: ADMIN_EMAIL / ADMIN_PASSWORD duoi day.\n')
    return env, app


def dong_goi() -> bytes:
    buf = io.BytesIO()

    def loc(ti: tarfile.TarInfo):
        return None if any(p in BO_QUA or p.endswith('.pyc') for p in Path(ti.name).parts) else ti

    with tarfile.open(fileobj=buf, mode='w:gz') as tar:
        for ten in DUA_LEN:
            tar.add(GOC / ten, arcname=ten, filter=loc)
    return buf.getvalue()


def trien_khai():
    t0 = time.time()
    env, app = chuan_bi_bien()
    goi = dong_goi()
    print(f'Dong goi ma nguon: {len(goi) / 1e6:.1f} MB')
    ma, _ = ssh(f'mkdir -p {THU_MUC_VPS} && chmod 700 {THU_MUC_VPS}')
    if ma:
        sys.exit('Khong SSH duoc vao VPS')
    gui_tep(goi, f'{THU_MUC_VPS}/src.tar.gz')
    ssh(f'cd {THU_MUC_VPS} && rm -rf src.moi && mkdir src.moi && tar xzf src.tar.gz -C src.moi '
        f'&& rm -rf src && mv src.moi src && rm src.tar.gz')
    gui_tep((DAY / 'docker-compose.yml').read_bytes(), f'{THU_MUC_VPS}/docker-compose.yml', '644')
    gui_tep((DAY / '.env').read_bytes(), f'{THU_MUC_VPS}/.env')
    gui_tep((DAY / 'app.env').read_bytes(), f'{THU_MUC_VPS}/app.env')
    print('Build va chay (lan dau mat 5-10 phut vi phai dong goi game sang WebAssembly)...')
    ma, out = ssh(f"bash -c 'set -o pipefail; cd {THU_MUC_VPS} && docker compose up -d --build 2>&1 | tail -25'")
    if ma:
        sys.exit('docker compose loi, xem o tren')
    print('Cho may chu game san sang...')
    for _ in range(60):
        ma, out = ssh("docker exec sukydieutra_app python -c \"import urllib.request as u;"
                      "print(u.urlopen('http://127.0.0.1:8000/health', timeout=5).read().decode())\"",
                      in_ra=False)
        if ma == 0 and '"database"' in out:
            print('health:', out.strip())
            break
        time.sleep(5)
    else:
        print('May chu chua san sang sau 5 phut. Xem: python trien_khai_vps/day_len_vps.py --nhat-ky app')
    trang_thai()
    print(f'Xong ({time.time() - t0:.0f}s). Trang game: {app["WEB_BASE_URL"]}  |  quan tri: https://{app["ADMIN_HOST"]}')


def trang_thai():
    ssh(f"cd {THU_MUC_VPS} && docker compose ps --format '{{{{.Name}}}}  {{{{.Status}}}}'")
    ssh("docker logs sukydieutra_tunnel 2>&1 | grep -iE 'Registered tunnel connection|error|ERR' | tail -4")


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    a = sys.argv[1:]
    if not a:
        trien_khai()
    elif a[0] == '--trang-thai':
        trang_thai()
    elif a[0] == '--nhat-ky':
        ten = {'app': 'sukydieutra_app', 'tunnel': 'sukydieutra_tunnel', 'db': 'sukydieutra_db'}[a[1] if len(a) > 1 else 'app']
        ssh(f'docker logs --tail 60 {ten} 2>&1')
    elif a[0] == '--dung':
        ssh(f'cd {THU_MUC_VPS} && docker compose down')
    elif a[0] == '--go-sach':
        if '--that' not in a:
            sys.exit('Lenh nay XOA HAN game tren VPS (ca CSDL nguoi choi, anh). Chac chan thi them --that')
        ssh(f'cd {THU_MUC_VPS} && docker compose down -v --rmi local; cd / && rm -rf {THU_MUC_VPS}')
        print('Da go. Con lai tren Cloudflare: Networking > Tunnels > sukydieutra > Delete (xoa ca ten mien game/admin).')
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
