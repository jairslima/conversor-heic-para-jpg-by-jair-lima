from __future__ import annotations

import argparse
import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


DEFAULT_ROOT = Path.home() / "Pictures"
JPG_EXTENSIONS = {".jpg", ".jpeg"}
WINDOWS_EPOCH_OFFSET = 116444736000000000
STATE_FILE_NAME = "heic_converter_state.json"
SCAN_PROGRESS_INTERVAL_SECONDS = 0.35


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def state_file_path() -> Path:
    return app_dir() / STATE_FILE_NAME


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Converte arquivos HEIC para JPG quando o equivalente ainda nao existe."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help=f"Pasta raiz da varredura. Padrao: {DEFAULT_ROOT}",
    )
    parser.add_argument(
        "--ffmpeg",
        default="ffmpeg",
        help="Comando ou caminho do ffmpeg. Padrao: ffmpeg",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reconverte mesmo se o JPG equivalente ja existir.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra o que faria, sem converter arquivos.",
    )
    parser.add_argument(
        "--restart",
        action="store_true",
        help="Ignora o estado salvo e reinicia a varredura do inicio.",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Nao tenta continuar a execucao anterior, mesmo se houver estado salvo.",
    )
    parser.add_argument(
        "--pause-on-finish",
        action="store_true",
        help="Aguarda Enter ao terminar, util para execucao por duplo clique.",
    )
    return parser.parse_args()


@dataclass
class Stats:
    found: int = 0
    converted: int = 0
    skipped_existing: int = 0
    failed: int = 0


def log(message: str) -> None:
    print(message, flush=True)


def render_progress(prefix: str, current: int, total: int) -> str:
    if total <= 0:
        return f"{prefix}: {current}"
    percent = (current / total) * 100
    return f"{prefix}: {current}/{total}, {percent:5.1f}%"


def format_relative_folder(root: Path, source: Path) -> str:
    try:
        relative_parent = source.parent.relative_to(root)
    except ValueError:
        return str(source.parent)

    if str(relative_parent) == ".":
        return str(root)
    return str(Path(root.name) / relative_parent)


def shorten_text(value: str, max_length: int = 90) -> str:
    if len(value) <= max_length:
        return value
    keep = max_length - 3
    left = keep // 2
    right = keep - left
    return f"{value[:left]}...{value[-right:]}"


def set_console_title(title: str) -> None:
    if os.name != "nt":
        return
    try:
        ctypes.windll.kernel32.SetConsoleTitleW(title)
    except Exception:
        return


def ensure_ffmpeg(ffmpeg_cmd: str) -> None:
    if shutil.which(ffmpeg_cmd):
        return
    if Path(ffmpeg_cmd).exists():
        return
    raise FileNotFoundError(f"ffmpeg nao encontrado: {ffmpeg_cmd}")


def collect_heic_files(root: Path) -> list[Path]:
    items: list[Path] = []
    scanned_dirs = 0
    last_report = 0.0

    for current_root, dirs, files in os.walk(root):
        dirs.sort(key=str.casefold)
        files.sort(key=str.casefold)
        scanned_dirs += 1

        for file_name in files:
            path = Path(current_root) / file_name
            if path.suffix.lower() == ".heic":
                items.append(path)

        now = time.monotonic()
        if now - last_report >= SCAN_PROGRESS_INTERVAL_SECONDS:
            sys.stdout.write(
                "\rMapeando arquivos... "
                f"pastas: {scanned_dirs}, heic encontrados ate agora: {len(items)}"
            )
            sys.stdout.flush()
            last_report = now

    items.sort(key=lambda item: str(item).casefold())
    if scanned_dirs:
        sys.stdout.write(
            "\rMapeando arquivos... "
            f"pastas: {scanned_dirs}, heic encontrados ate agora: {len(items)}"
        )
        sys.stdout.flush()
        print()
    return items


def find_existing_jpg(source: Path) -> Path | None:
    for candidate in source.parent.iterdir():
        if not candidate.is_file():
            continue
        if candidate.stem.casefold() != source.stem.casefold():
            continue
        if candidate.suffix.lower() in JPG_EXTENSIONS:
            return candidate
    return None


def windows_filetime_from_timestamp(timestamp: float) -> int:
    return int(timestamp * 10_000_000) + WINDOWS_EPOCH_OFFSET


def set_creation_time_windows(target: Path, timestamp: float) -> None:
    handle = ctypes.windll.kernel32.CreateFileW(
        str(target),
        256,
        0,
        None,
        3,
        128,
        None,
    )
    if handle == -1:
        raise OSError(f"Nao foi possivel abrir arquivo para ajustar criacao: {target}")

    try:
        ft = windows_filetime_from_timestamp(timestamp)
        file_time = ctypes.c_ulonglong(ft)
        if not ctypes.windll.kernel32.SetFileTime(
            handle,
            ctypes.byref(file_time),
            None,
            None,
        ):
            raise OSError(f"Nao foi possivel ajustar criacao do arquivo: {target}")
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def sync_timestamps(source: Path, target: Path) -> None:
    stat = source.stat()
    os.utime(target, (stat.st_atime, stat.st_mtime))
    if os.name == "nt":
        set_creation_time_windows(target, stat.st_ctime)


def build_ffmpeg_command(ffmpeg_cmd: str, source: Path, destination: Path) -> list[str]:
    return [
        ffmpeg_cmd,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-map_metadata",
        "0",
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(destination),
    ]


def convert_one(source: Path, target: Path, ffmpeg_cmd: str) -> None:
    with tempfile.NamedTemporaryFile(
        suffix=".jpg",
        dir=target.parent,
        delete=False,
    ) as tmp:
        temp_target = Path(tmp.name)

    try:
        command = build_ffmpeg_command(ffmpeg_cmd, source, temp_target)
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            stderr = result.stderr.strip() or "ffmpeg falhou sem detalhes."
            raise RuntimeError(stderr)

        temp_target.replace(target)
        sync_timestamps(source, target)
    except Exception:
        if temp_target.exists():
            temp_target.unlink()
        raise


def load_state() -> dict | None:
    state_file = state_file_path()
    if not state_file.exists():
        return None
    return json.loads(state_file.read_text(encoding="utf-8"))


def save_state(root: Path, last_processed: str | None) -> None:
    payload = {
        "root": str(root),
        "last_processed": last_processed,
    }
    state_file_path().write_text(
        json.dumps(payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def clear_state() -> None:
    state_file = state_file_path()
    if state_file.exists():
        state_file.unlink()


def resolve_resume_index(files: list[Path], root: Path, args: argparse.Namespace) -> int:
    if args.restart:
        clear_state()
        log("Reinicio solicitado, o estado salvo foi ignorado.")
        return 0

    if args.no_resume:
        log("Continuacao automatica desativada para esta execucao.")
        return 0

    state = load_state()
    if not state:
        return 0

    saved_root = Path(state.get("root", ""))
    if saved_root != root:
        log("Estado salvo encontrado para outra pasta, a execucao atual vai iniciar do comeco.")
        return 0

    last_processed = state.get("last_processed")
    if not last_processed:
        return 0

    lookup = str(last_processed).casefold()
    for index, item in enumerate(files):
        if str(item).casefold() == lookup:
            resume_from = index + 1
            log(f"Continuando da execucao anterior, a partir do item {resume_from + 1}.")
            return resume_from

    log("O ultimo arquivo salvo nao foi encontrado, a execucao atual vai iniciar do comeco.")
    return 0


def pause_if_requested(args: argparse.Namespace) -> None:
    if args.pause_on_finish:
        input("Pressione Enter para sair...")


def print_controls() -> None:
    log("Controles:")
    log("1. Ctrl+C salva o progresso atual e encerra.")
    log("2. Execute novamente sem parametros para continuar automaticamente.")
    log("3. Use --restart para recomecar do inicio.")


def main() -> int:
    args = parse_args()
    root = args.root.expanduser().resolve()

    try:
        ensure_ffmpeg(args.ffmpeg)
    except FileNotFoundError as exc:
        print(f"ERRO: {exc}", file=sys.stderr, flush=True)
        pause_if_requested(args)
        return 2

    if not root.exists():
        print(f"ERRO: pasta raiz nao encontrada: {root}", file=sys.stderr, flush=True)
        pause_if_requested(args)
        return 2

    log("Inicializando o conversor...")
    log(f"Pasta alvo: {root}")
    log("Iniciando mapeamento dos arquivos HEIC...")

    stats = Stats()
    files = collect_heic_files(root)
    resume_index = resolve_resume_index(files, root, args)
    pending_files = files[resume_index:]

    print_controls()
    log(f"HEIC localizados nesta pasta: {len(files)}")
    log(f"HEIC pendentes nesta execucao: {len(pending_files)}")
    if args.dry_run:
        log("Modo simulacao ativo, nenhum arquivo sera convertido.")

    try:
        last_folder_shown: str | None = None
        for index, source in enumerate(pending_files, start=1):
            stats.found += 1
            existing = find_existing_jpg(source)
            target = source.with_suffix(".jpg")
            progress = render_progress("Progresso", index, len(pending_files))
            current_folder = format_relative_folder(root, source)
            folder_display = shorten_text(current_folder, max_length=70)
            set_console_title(f"Conversor HEIC JPG, {folder_display}")

            if current_folder != last_folder_shown:
                log(f"Pasta atual: {current_folder}")
                last_folder_shown = current_folder

            if existing and not args.force:
                stats.skipped_existing += 1
                log(f"{progress}, pasta: {folder_display}, IGNORADO: {source.name}")
                save_state(root, str(source))
                continue

            if args.dry_run:
                log(f"{progress}, pasta: {folder_display}, SIMULAR: {source.name}")
                save_state(root, str(source))
                continue

            try:
                convert_one(source, target, args.ffmpeg)
                stats.converted += 1
                log(f"{progress}, pasta: {folder_display}, OK: {source.name}")
            except Exception as exc:
                stats.failed += 1
                print(
                    f"{progress}, pasta: {folder_display}, FALHA: {source.name} -> {exc}",
                    file=sys.stderr,
                    flush=True,
                )
            finally:
                save_state(root, str(source))
    except KeyboardInterrupt:
        print(flush=True)
        log("Pausa solicitada, o progresso foi salvo para continuar na proxima execucao.")
        pause_if_requested(args)
        return 130

    clear_state()
    print(flush=True)
    log("Resumo:")
    log(f"HEIC analisados nesta execucao: {stats.found}")
    log(f"JPG convertidos: {stats.converted}")
    log(f"Ja existentes: {stats.skipped_existing}")
    log(f"Falhas: {stats.failed}")
    log("Execucao concluida, sem estado pendente.")

    pause_if_requested(args)
    return 1 if stats.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
