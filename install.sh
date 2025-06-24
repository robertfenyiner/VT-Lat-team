#!/bin/bash

set -e

echo "📦 Instalando dependencias del sistema..."

sudo apt update && sudo apt install -y \
  python3-venv python3-pip ffmpeg mkvtoolnix \
  mkvtoolnix-gui mediainfo libmediainfo-dev \
  ccextractor curl unzip aria2 cmake g++ git

echo "🧰 Instalando Poetry..."

if ! command -v poetry &>/dev/null; then
  curl -sSL https://install.python-poetry.org | python3 -
  export PATH="$HOME/.local/bin:$PATH"
fi

echo "🐍 Configurando entorno virtual con Poetry..."

poetry config virtualenvs.in-project true

if [ ! -f poetry.lock ]; then
  poetry lock
else
  poetry lock --no-update
fi

poetry install

echo "✅ Entorno preparado. Ejecuta con:"
echo "  poetry run python -m vinetrimmer.vinetrimmer --help"
echo ""

echo "🔍 Verificando binarios externos necesarios..."

BIN_DIR="$PWD/binaries"
MISSING=0

check_bin() {
  if command -v "$1" &>/dev/null; then
    echo "✅ $1 encontrado en el sistema"
  elif [ -x "$BIN_DIR/$1" ]; then
    echo "✅ $1 encontrado en $BIN_DIR/"
  else
    echo "❌ $1 no encontrado"
    MISSING=1
  fi
}

check_bin ffmpeg
check_bin mp4decrypt
check_bin mkvmerge
check_bin aria2c
check_bin ccextractor

# Intentar compilar mp4decrypt si no se encuentra
if [ ! -x "$BIN_DIR/mp4decrypt" ]; then
  echo "⚙️ Compilando mp4decrypt desde Bento4..."

  TMP_DIR=$(mktemp -d)
  git clone https://github.com/axiomatic-systems/Bento4.git "$TMP_DIR/Bento4"
  cd "$TMP_DIR/Bento4"
  mkdir -p build && cd build
  cmake ..
  make

  if [ -f ./mp4decrypt ]; then
    echo "✅ mp4decrypt compilado correctamente"
    cp ./mp4decrypt "$BIN_DIR/"
    chmod +x "$BIN_DIR/mp4decrypt"
  else
    echo "❌ Error: no se pudo compilar mp4decrypt"
  fi

  cd "$PWD"
fi

echo "📂 Agregando '$BIN_DIR' al PATH temporalmente..."
export PATH="$BIN_DIR:$PATH"

echo ""
echo "🚀 Instalación completa. Puedes ejecutar ahora:"
echo "  poetry run python -m vinetrimmer.vinetrimmer --help"
