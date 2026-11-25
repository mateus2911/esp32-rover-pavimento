import argparse
import os
import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inicia o servidor do Rover de Inspeção de Pavimento."
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--real",
        action="store_true",
        help="Conecta na ESP32 real (força ROVER_MOCK_MODE=false).",
    )
    mode_group.add_argument(
        "--mock",
        action="store_true",
        help="Executa em modo simulação sem hardware (força ROVER_MOCK_MODE=true).",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host do servidor FastAPI.")
    parser.add_argument("--port", type=int, default=8000, help="Porta HTTP do servidor.")
    args = parser.parse_args()

    if args.real:
        os.environ["ROVER_MOCK_MODE"] = "false"
    elif args.mock:
        os.environ["ROVER_MOCK_MODE"] = "true"

    uvicorn.run("backend.main:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
