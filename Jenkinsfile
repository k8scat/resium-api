def remoteConfig = [:]
remoteConfig.name = "${env.REMOTE_HOST}"
remoteConfig.host = "${env.REMOTE_HOST}"
remoteConfig.port = 2222
remoteConfig.allowAnyHosts = true

node {
  // 使用当前项目下的凭据管理中的 用户名 + 密码 凭据
  withCredentials([usernamePassword(
    credentialsId: "${env.REMOTE_CRED}",
    passwordVariable: 'password',
    usernameVariable: 'userName'
  )]) {

    // SSH 登陆用户名
    remoteConfig.user = userName
    // SSH 登陆密码
    remoteConfig.password = password

    stage("通过 SSH 执行命令") {
      sshCommand(remote: remoteConfig, command: 'rm -rf resium && git clone git@e.coding.net:hsowan/resium/resium.git && cd resium && /bin/bash deploy.sh')
    }
  }
}