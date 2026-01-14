# /// script
# requires-python = ">=3.11"
# dependencies = ["rich", "click"]
# ///

import click
from pathlib import Path
import os
from rich import print as rprint
import sys
import shutil
import asyncio
from dataclasses import dataclass
from rich.padding import Padding

MC_SCRIPTS_DIR = "mc_scripts"


@dataclass
class Result:
    filename: str
    returncode: int
    stdout: str
    stderr: str


async def _process_lua(filename: str, output_path: str) -> Result:
    cmd = (
        ["darklua", "process"]
        + [f"src/{MC_SCRIPTS_DIR}/{filename}"]
        + [f"{output_path}/{filename}"]
    )
    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return Result(
        filename=filename, returncode=process.returncode, stdout=stdout, stderr=stderr
    )


async def _process_mc_scripts(project_path: str, output_path: str) -> None:
    src_dir = f"{project_path}/src/{MC_SCRIPTS_DIR}"
    files = os.listdir(src_dir)
    lua_files = [x for x in files if x.endswith(".lua")]

    tasks = [_process_lua(lua_file, output_path) for lua_file in lua_files]
    results = await asyncio.gather(*tasks)

    completed = 0

    for result in results:
        if result.returncode == 0:
            rprint(f"{result.filename}: [green]OK[/green]")
            completed = completed + 1
        else:
            rprint(f"{result.filename}: [red]Error[/red]")
            rprint(Padding(result.stderr.decode("utf-8").strip(), (0, 0, 2, 2)))

    if completed > 0:
        if results:
            rprint(
                f"Done! Output is saved to: [bold yellow]{output_path}[/bold yellow]"
            )
        else:
            rprint(
                f"Nothing to do; no scripts in [bold yellow]{src_dir}[/bold yellow]."
            )


@click.command()
@click.argument("project_dir", type=click.Path(exists=True))
def process_mc_scripts(project_dir: str) -> None:
    if project_dir.startswith(".."):
        rprint("[red]Error:[/red] Path traversal upwards is not supported.")
        sys.exit(1)

    if project_dir == ".":
        project_path = str(Path.cwd())
    else:
        project_path = os.path.abspath(project_dir)

    output_path = f"{project_path}/build/{MC_SCRIPTS_DIR}"

    # Remove previously processed scripts if they exist
    if Path(output_path).is_dir():
        shutil.rmtree(output_path)

    # Create the output directory
    Path(f"{project_path}/build").mkdir(parents=False, exist_ok=True)
    Path(output_path).mkdir(parents=False, exist_ok=False)

    asyncio.run(_process_mc_scripts(project_path, output_path))


if __name__ == "__main__":
    process_mc_scripts()
