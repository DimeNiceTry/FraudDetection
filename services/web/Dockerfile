FROM nginx:alpine

# Копируем статические файлы в директорию Nginx
COPY . /usr/share/nginx/html/

# Копируем настройки Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"] 