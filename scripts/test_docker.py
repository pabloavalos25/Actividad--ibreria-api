"""Pruebas Docker del TP con PostgreSQL externo NUEVO y limpieza de recursos propios.

No acepta URL ni directorio de datos existente, no lee .env y no ejecuta seed.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

import asyncpg


ROOT = Path(__file__).resolve().parents[1]


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    default_docker = shutil.which("docker") or str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/DockerDesktop/resources/bin/docker.exe")
    parser.add_argument("--docker", default=default_docker)
    parser.add_argument("--pg-bin", type=Path, default=Path("C:/Program Files/PostgreSQL/17/bin"))
    args = parser.parse_args()
    token = uuid.uuid4().hex[:12]
    directory = (ROOT / "tmp" / f"docker-tests-{token}").resolve()
    assert directory.is_relative_to((ROOT / "tmp").resolve())
    directory.mkdir(parents=True, exist_ok=False)
    data = directory / "data"
    evidence = []
    environment = dict(os.environ)
    environment["PATH"] = str(Path(args.docker).parent) + os.pathsep + environment.get("PATH", "")
    environment.pop("DATABASE_URL", None)
    environment.pop("PGDATA", None)
    image = f"codex-tp-{token}"
    containers = []
    pg_port, app_port = free_port(), free_port()
    assert pg_port != 5432
    pg_user, database = "docker_test", "libreria_docker_test"
    env_file = directory / "runtime.env"
    env_file.write_text(f"DATABASE_URL=postgresql+asyncpg://{pg_user}@host.docker.internal:{pg_port}/{database}\nECHO_SQL=false\n", encoding="utf-8")
    initialized = False

    def record(message):
        evidence.append(message)
        print(message, flush=True)

    def run(command, *, expected=0, input_text=None, timeout=180):
        shown = [str(part).replace(str(directory), "<TEMP>") for part in command]
        record("$ " + subprocess.list2cmdline(shown))
        result = subprocess.run(command, cwd=ROOT, env=environment, input=input_text,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                encoding="utf-8", errors="replace", timeout=timeout,
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        record(result.stdout.rstrip())
        if expected is not None:
            assert result.returncode == expected, (result.returncode, result.stdout)
        return result

    def docker(*parts, **kwargs):
        if parts and parts[0] == "run" and "--name" not in parts:
            name = f"codex-tp-{token}-transient-{len(containers)}"
            containers.append(name)
            parts = (parts[0], "--name", name, *parts[1:])
        return run([args.docker, *map(str, parts)], **kwargs)

    def pg(action):
        command = [str(args.pg_bin / ("pg_ctl.exe" if os.name == "nt" else "pg_ctl")), "-D", str(data)]
        if action == "start":
            command += ["-l", str(directory / "postgres.log"), "-o", f"-h 0.0.0.0 -p {pg_port} -c max_connections=20", "-w", "start"]
        else:
            command += ["-m", "fast", "-w", "stop"]
        # pg_ctl inherits handles into postgres: a disk file avoids PIPE waiting on the server.
        record("$ " + subprocess.list2cmdline(command).replace(str(directory), "<TEMP>"))
        with (directory / "pg-command.log").open("w", encoding="utf-8") as output:
            result = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, env=environment,
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        record((directory / "pg-command.log").read_text(encoding="utf-8", errors="replace").rstrip())
        result.check_returncode()

    async def query(sql, *, db=database):
        connection = await asyncpg.connect(host="127.0.0.1", port=pg_port, user=pg_user, database=db, timeout=5)
        try:
            actual = await connection.fetchval("SHOW data_directory")
            assert Path(actual).resolve() == data.resolve(), "Servidor ajeno al cluster propio"
            return await connection.fetch(sql)
        finally:
            await connection.close()

    def container_run(*parts, name=None):
        name = name or f"codex-tp-{token}-{len(containers)}"
        containers.append(name)
        return docker("run", "--name", name, *parts)

    def inspect(name):
        return json.loads(docker("inspect", name).stdout)[0]

    def healthy(name):
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            state = json.loads(subprocess.check_output([args.docker, "inspect", "--format", "{{json .State}}", name], env=environment, text=True))
            if state.get("Health", {}).get("Status") == "healthy":
                record(f"HEALTHY {name}")
                return
            assert state["Running"], docker("logs", name).stdout
            time.sleep(1)
        raise AssertionError(f"No healthy: {name}")

    def http(path, body=None):
        payload = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(f"http://127.0.0.1:{app_port}{path}", data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=5) as response:
            result = json.load(response)
            record(f"HTTP {response.status} {path}: {json.dumps(result, ensure_ascii=True)}")
            return result

    def alembic(*parts):
        return docker("run", "--rm", "--env-file", env_file, "--entrypoint", "alembic", image, *parts)

    try:
        record("Ejercicio 9: evidencia LOCAL real; no acredita VPS ni seed. Credenciales temporales sin secretos reales.")
        docker("version", "--format", "{{.Client.Version}} / {{.Server.Version}}")
        docker("build", "--progress=plain", "-t", image, ROOT / "despliegue", timeout=600)
        base = json.loads(docker("image", "inspect", "python:3.12-alpine").stdout)[0]
        final = json.loads(docker("image", "inspect", image).stdout)[0]
        assert base["Size"] < 100_000_000
        assert not any(item.startswith(("DATABASE_URL=", "POSTGRES_PASSWORD=")) for item in final["Config"]["Env"])
        record(f"D-01 base_bytes={base['Size']} final_bytes={final['Size']} base_id={base['Id']}")
        history = docker("history", "--no-trunc", image).stdout
        assert "postgresql+asyncpg://" not in history
        result = docker("run", "--rm", "--entrypoint", "python", image, "-c", "import os,pathlib,shutil; assert os.getuid()!=0; assert not pathlib.Path('/app/.env').exists(); assert 'DATABASE_URL' not in os.environ; assert len(list(pathlib.Path('/app/migrations/versions').glob('*.py')))==2; assert not any(shutil.which(c) for c in ('gcc','cc','make')); print('D-06/D-07 uid=',os.getuid(),'; sin .env/URL/compilador; dos migraciones')")
        assert "uid=" in result.stdout

        # A real BuildKit COPY context, with harmless canaries in a fresh copy only.
        context = directory / "context"
        shutil.copytree(ROOT / "despliegue", context, ignore=shutil.ignore_patterns(".env", ".env.*", ".venv", "__pycache__", ".git"))
        probe = context / "canary"
        for relative in (".env", ".venv/secret.txt", ".git/secret.txt", "__pycache__/secret.pyc"):
            path = probe / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("HARMLESS-CONTEXT-CANARY", encoding="utf-8")
        (probe / "visible.txt").write_text("visible", encoding="utf-8")
        exported = directory / "context-export"
        docker("build", "--progress=plain", "--output", f"type=local,dest={exported}", "-f", "-", context,
               input_text="FROM scratch\nCOPY . /\n")
        assert (exported / "canary/visible.txt").is_file()
        assert not any(p.name in {".env", ".venv", ".git", "__pycache__"} for p in exported.rglob("*"))
        record("Contexto BuildKit: archivo visible presente; los cuatro señuelos excluidos realmente.")

        missing_name = f"codex-tp-{token}-missing"
        containers.append(missing_name)
        missing = docker("run", "--name", missing_name, image, expected=None)
        assert missing.returncode != 0 and "Uvicorn running" not in missing.stdout
        record("D-05 sin DATABASE_URL: salida no cero, sin servidor HTTP.")
        dead_name = f"codex-tp-{token}-dead"
        containers.append(dead_name)
        dead = docker("run", "--name", dead_name, "-e", "DATABASE_URL=postgresql+asyncpg://test@127.0.0.1:1/inaccesible", image, expected=None)
        assert dead.returncode != 0 and "Uvicorn running" not in dead.stdout
        record("Base inaccesible: salida no cero, sin servidor HTTP.")

        run([str(args.pg_bin / ("initdb.exe" if os.name == "nt" else "initdb")), "-D", str(data), "-U", pg_user, "--auth=trust", "--encoding=UTF8", "--no-locale"])
        initialized = True
        with (data / "pg_hba.conf").open("a", encoding="utf-8") as hba:
            hba.write("\n# Solo cluster temporal propio para Docker Desktop\nhost all all 0.0.0.0/0 trust\n")
        pg("start")
        asyncio.run(query(f"CREATE DATABASE {database}", db="postgres"))
        alembic("upgrade", "head")
        alembic("check")
        alembic("downgrade", "base")
        assert not asyncio.run(query("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename!='alembic_version'"))
        alembic("upgrade", "head")
        alembic("check")
        record("Migraciones TP: head/check/base vacío/head/check aprobados.")
        alembic("downgrade", "base")
        assert not asyncio.run(query("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename!='alembic_version'"))

        first = f"codex-tp-{token}-app1"
        def start_app(name):
            container_run("-d", "--env-file", env_file, "-p", f"127.0.0.1:{app_port}:8000", "--restart", "unless-stopped", image, name=name)
            healthy(name)
            assert inspect(name)["HostConfig"]["RestartPolicy"]["Name"] == "unless-stopped"
            http("/health/ready")
        start_app(first)
        first_logs = docker("logs", first).stdout
        assert "Running upgrade" in first_logs
        assert "846f445b2248" in first_logs and "332ba12e013b" in first_logs
        record("Primer entrypoint contra base vacía aplicó automáticamente las dos migraciones TP.")
        editorial = http("/editoriales/", {"nombre": f"Testigo-{token}", "pais": "Pruebas"})
        docker("exec", first, "id")
        pg("stop")
        try:
            http("/health/ready")
            raise AssertionError("Ready no detectó caída PostgreSQL")
        except urllib.error.HTTPError as error:
            assert error.code == 503
            record("Ready con PostgreSQL detenido: HTTP 503.")
        check = docker("exec", first, "python", "/app/healthcheck.py", expected=None)
        assert check.returncode != 0
        record("HEALTHCHECK ante caída DB: salida no cero.")
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            health = subprocess.check_output([args.docker, "inspect", "--format", "{{.State.Health.Status}}", first], env=environment, text=True).strip()
            if health == "unhealthy":
                record("Estado Docker pasó a unhealthy con PostgreSQL detenido.")
                break
            time.sleep(1)
        else:
            raise AssertionError("Estado Docker no pasó a unhealthy")
        pg("start")
        healthy(first)
        docker("rm", "-f", first)
        second = f"codex-tp-{token}-app2"
        start_app(second)
        assert http(f"/editoriales/{editorial['id']}")["nombre"] == editorial["nombre"]
        logs = docker("logs", second).stdout
        assert "Running upgrade" not in logs
        record("Recreación: testigo persiste; no Running upgrade; contratos TP sin auth del parcial.")
        record("RESULTADO: todas las verificaciones locales Docker aprobadas. D-02/03/04/08 VPS siguen pendientes.")
    finally:
        for name in containers:
            docker("rm", "-f", name, expected=None)
        docker("image", "rm", image, expected=None)
        if initialized and (data / "postmaster.pid").exists():
            pg("stop")
        assert not (data / "postmaster.pid").exists(), "Cluster propio todavía activo"
        record("Limpieza final: containers/imagen propios eliminados; PostgreSQL propio detenido. Base Python compartida conservada.")
        output = ROOT / "despliegue/evidencia/docker_local.txt"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("\n".join(evidence) + "\n", encoding="utf-8")
        (directory / "verification.txt").write_text("\n".join(evidence), encoding="utf-8")


if __name__ == "__main__":
    main()
