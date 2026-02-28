# Troubleshooting

## `host.docker.internal` connection issues

Use DevContainer / Docker Desktop as documented.

## IPFS restart loop

Use `ipfs/kubo:latest` in `ipfs/docker-compose.yaml`.

## `/mobile` not reachable from smartphone

- Start frontend with `--host 0.0.0.0`
- Confirm same Wi-Fi network
- Check firewall rule for `5173`
