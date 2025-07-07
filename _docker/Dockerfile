# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

# Cài đặt biến môi trường không sinh ra pyc
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Tạo user không phải root
RUN useradd -m botuser

WORKDIR /app

# Copy requirements trước để cache layer
COPY requirements.txt ./

# Cài đặt các dependencies Python
RUN pip install --no-cache-dir -r requirements.txt

# Copy mã nguồn, loại trừ file/folder không cần thiết (dựa trên .dockerignore nếu có)
COPY . .

# Đảm bảo quyền cho user không phải root
RUN chown -R botuser:botuser /app

# Expose cổng dummy (không cần thiết cho bot, chỉ để monitor container)
EXPOSE 8080

USER botuser

ENTRYPOINT ["python", "main.py"] 