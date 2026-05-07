# WSL2 systemd 활성화 가이드

`bash start.sh` 실행 시 WSL2 systemd가 비활성화되어 있으면 자동 패치를 안내합니다.
아래 단계를 따라 수동으로 설정할 수도 있습니다.

## 빠른 설정

1. WSL2 안에서:
   ```bash
   sudo nano /etc/wsl.conf
   ```
2. 다음 내용 추가 (기존 `[boot]` 섹션이 있으면 그 아래에, 없으면 새로 추가):
   ```ini
   [boot]
   systemd=true
   ```
3. Windows PowerShell에서:
   ```powershell
   wsl --shutdown
   ```
4. WSL2 재시작 후 다시 실행:
   ```bash
   bash start.sh
   ```

## 검증

```bash
systemctl --user status   # 정상 출력되어야 함
loginctl show-user "$USER" | grep Linger   # Linger=yes 확인
```

## 왜 systemd가 필요한가?

- WSL2는 터미널 창을 모두 닫으면 distro를 자동 종료합니다.
- `nohup` 으로 실행된 watcher/webhook 프로세스도 함께 종료됩니다.
- `systemd --user` + `loginctl enable-linger` 를 사용하면 세션이 없어도 서비스가 살아있습니다.

## Windows 재부팅 후 자동 기동

WSL2가 Windows 재부팅 후 자동으로 시작되도록 하려면:

```powershell
# Windows PowerShell (관리자) 에서 실행
wsl -d Ubuntu --exec bash -c "systemctl --user start clickeye-watcher"
```

또는 `scripts/setup-autostart.ps1` 을 사용하세요:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup-autostart.ps1
```
