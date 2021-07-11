# Install mysqlclient on M1 Mac

下面将通过回忆以及日志来记录一下在 M1 Mac 上如何解决安装 `mysqlclient` 失败的问题。

## UPD

后来发现只要安装 `mysql-client` 就可以了：

```bash
arch -arm64 brew install mysql-client

pip install mysqlclient
```

但当我开始迁移数据库时，又有问题了：

```bash
# ./migrate/dev.sh
python manage.py makemigrations downloader

# 省略...
django.core.exceptions.ImproperlyConfigured: Error loading MySQLdb module.
Did you install mysqlclient?
```

各种尝试后作出以下改动：

- 修改依赖：`mysqlclient==1.4.4` -> `PyMySQL==1.0.2`
- 同时在 [__init__.py](./resium/settings/__ini__.py) 文件中添加以下内容：

```python
import pymysql
pymysql.install_as_MySQLdb()
```

这样就可以正常执行迁移了！

## 安装过程

一开始的安装命令：

```bash
pip install mysqlclient==1.4.4
```

安装 `mysqlclient` 会出现下面的问题：

```txt
mysql_config not found
```

这个问题可以通过在本地安装 `mysql` 来解决：

```bash
$ brew install mysql
Error: Cannot install under Rosetta 2 in ARM default prefix (/opt/homebrew)!
To rerun under ARM use:
    arch -arm64 brew install ...
To install under x86_64, install Homebrew into /usr/local.
```

根据第一次安装失败的提示，进行了第二次安装：

```bash
arch -arm64 brew install mysql
```

然后再尝试安装 `mysqlclient` 时又出现了下面的问题：

```txt
ld: library not found for -lzstd
```

通过 [参看内容1](#参考内容)，知道了需要安装 `zstd`：

```bash
brew install zstd
```

安装完 `zstd` 后重新尝试安装 `mysqlclient`，但仍是那个错误 `ld: library not found for -l`，然后通过 [参看内容2](#参考内容) 得知，可以通过 `env` 设置环境变量指定依赖库的位置：

```bash
env LDFLAGS="-L/opt/homebrew/Cellar/zstd/1.5.0/lib" pip install mysqlclient==1.4.4
```

这时发现类似的问题：

```txt
ld: library not found for -lssl
```

然后在 [参看内容2](#参考内容) 中可以得知需要安装 `openssl`：

```bash
brew install openssl
```

在确认已经安装 `openssl` 后，再尝试安装 `mysqlclient`，发现问题仍没有解决，这时再通过 `env` 设置一下 `openssl` 依赖库的位置：

```bash
env LDFLAGS="-L/opt/homebrew/Cellar/zstd/1.5.0/lib -L/opt/homebrew/Cellar/openssl@1.1/1.1.1k/lib" pip install mysqlclient==1.4.4
```

到这里就成功安装了 `mysqlclient`！

## 参考内容

1. [ld: library not found for -lzstd while bundle install for mysql2 gem Ruby on macOS Big Sur 11.4](https://stackoverflow.com/questions/67840691/ld-library-not-found-for-lzstd-while-bundle-install-for-mysql2-gem-ruby-on-mac)
2. [error install mysqlclient with pip, library not found for -lssl](https://stackoverflow.com/questions/51701051/error-install-mysqlclient-with-pip-library-not-found-for-lssl)
