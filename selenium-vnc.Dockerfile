# https://github.com/SeleniumHQ/docker-selenium

FROM selenium/standalone-chrome:4.0.0-rc-1-prerelease-20210618

RUN x11vnc -storepasswd X4xMsbJNx4sf3LJaBtrKmRzq3LbRgR5C /home/seluser/.vnc/passwd