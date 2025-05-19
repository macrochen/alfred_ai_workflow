#!/bin/bash

# 获取工作流名称
WORKFLOW_NAME=$(grep -A 1 "<key>name</key>" info.plist | grep "<string>" | sed 's/<string>\(.*\)<\/string>/\1/' | sed 's/ /_/g')
VERSION=$(grep -A 1 "<key>version</key>" info.plist | grep "<string>" | sed 's/<string>\(.*\)<\/string>/\1/')

if [ -z "$VERSION" ]; then
  VERSION="1.0.0"
fi

# 创建打包文件名
PACKAGE_NAME="${WORKFLOW_NAME}_v${VERSION}.alfredworkflow"

# 创建临时目录
TEMP_DIR="temp_package"
mkdir -p "$TEMP_DIR"

# 复制所有文件到临时目录，排除不需要的文件
rsync -av --exclude="$TEMP_DIR" --exclude=".git" --exclude=".gitignore" --exclude="*.alfredworkflow" --exclude="package.sh" --exclude="README.md" --exclude="LICENSE" ./ "$TEMP_DIR/"

# 进入临时目录并创建 zip 文件
cd "$TEMP_DIR"
zip -r "../$PACKAGE_NAME" ./*
cd ..

# 清理临时目录
rm -rf "$TEMP_DIR"

echo "打包完成: $PACKAGE_NAME"