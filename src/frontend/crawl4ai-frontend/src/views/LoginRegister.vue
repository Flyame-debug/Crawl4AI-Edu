<template>
  <div class="auth-container">
    <el-card class="auth-card">
      <el-tabs v-model="activeTab" stretch>
        <!-- 登录 -->
        <el-tab-pane label="登录" name="login">
          <el-form :model="loginForm" :rules="loginRules" ref="loginFormRef" label-width="80px">
            <el-form-item label="账号" prop="username">
              <el-input v-model="loginForm.username" placeholder="请输入账号"></el-input>
            </el-form-item>
            <el-form-item label="密码" prop="password">
              <el-input v-model="loginForm.password" type="password" placeholder="请输入密码"></el-input>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleLogin">登录</el-button>
            </el-form-item>
            <p class="switch-text">没有账号？<a @click="activeTab='register'">立即注册</a></p>
          </el-form>
        </el-tab-pane>

        <!-- 注册 -->
        <el-tab-pane label="注册" name="register">
          <el-form :model="registerForm" :rules="registerRules" ref="registerFormRef" label-width="80px">
            <el-form-item label="账号" prop="username">
              <el-input v-model="registerForm.username" placeholder="请输入账号"></el-input>
            </el-form-item>
            <el-form-item label="密码" prop="password">
              <el-input v-model="registerForm.password" type="password" placeholder="请输入密码"></el-input>
            </el-form-item>
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="registerForm.email" placeholder="请输入邮箱"></el-input>
              <el-button type="primary" @click="handleSendCode" style="margin-top: 10px;">
                发送验证码
              </el-button>
            </el-form-item>
            <el-form-item label="验证码" prop="email_code">
              <el-input v-model="registerForm.email_code" placeholder="请输入邮箱验证码"></el-input>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleRegister">注册</el-button>
            </el-form-item>
            <p class="switch-text">已有账号？<a @click="activeTab='login'">去登录</a></p>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script>
import { login, register, sendEmailCode } from '../api/auth'

export default {
  name: 'LoginRegisterPage',
  data() {
    return {
      activeTab: 'login',
      loginForm: { username: '', password: '' },
      registerForm: { username: '', password: '', email: '', email_code: '' },
      userInfo: { username: '默认用户', email: 'default@example.com', token: 'default-token' },
      loginRules: {
        username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
        password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
      },
      registerRules: {
        username: [
          { required: true, message: '请输入账号', trigger: 'blur' },
          { validator: this.validateUsername, trigger: 'blur' }
        ],
        password: [
          { required: true, message: '请输入密码', trigger: 'blur' },
          { validator: this.validatePassword, trigger: 'blur' }
        ],
        email: [
          { required: true, message: '请输入邮箱', trigger: 'blur' },
          { validator: this.validateEmail, trigger: 'blur' }
        ],
        email_code: [
          { required: true, message: '请输入验证码', trigger: 'blur' }
        ]
      }
    }
  },
  methods: {
    validateUsername(rule, value, callback) {
      if (value.length > 10) return callback(new Error('用户名不能超过10位'))
      return callback()
    },
    validatePassword(rule, value, callback) {
      const regex = /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$/
      if (!regex.test(value)) return callback(new Error('密码必须至少8位，且包含字母和数字'))
      return callback()
    },
    validateEmail(rule, value, callback) {
      const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      if (!regex.test(value)) return callback(new Error('邮箱格式不正确'))
      return callback()
    },

    // 登录：先显示默认数据，再覆盖
    handleLogin() {
      this.$refs.loginFormRef.validate(valid => {
        if (valid) {
          // 默认数据先写入
          this.userInfo = {
            username: this.loginForm.username || '默认用户',
            email: 'default@example.com',
            token: 'default-token'
          }
          localStorage.setItem('token', this.userInfo.token)
          localStorage.setItem('username', this.userInfo.username)
          localStorage.setItem('email', this.userInfo.email)
          this.$message.success('登录成功（默认数据）')
          this.$router.push('/home')

          // 真接口覆盖
          login(this.loginForm)
            .then(res => {
              if (res.data.success) {
                this.userInfo = res.data.user
                localStorage.setItem('token', res.data.token)
                localStorage.setItem('username', res.data.user.username)
                localStorage.setItem('email', res.data.user.email)
                this.$message.success('登录成功（后端数据覆盖）')
              }
            })
            .catch(() => {
              this.$message.error('登录失败')
            })
        }
      })
    },

    // 注册：先提示默认，再覆盖
    handleRegister() {
      this.$refs.registerFormRef.validate(valid => {
        if (valid) {
          this.$message.success(`注册成功（默认用户）`)
          this.activeTab = 'login'

          register(this.registerForm)
            .then(res => {
              if (res.data.success) {
                this.$message.success(res.data.message || `注册成功：用户ID ${res.data.userId}`)
                this.activeTab = 'login'
              }
            })
            .catch(() => {
              this.$message.error('注册失败')
            })
        }
      })
    },

    // 发送验证码
    handleSendCode() {
      if (!this.registerForm.email) {
        this.$message.error('请先输入邮箱')
        return
      }
      this.$message.success('验证码已发送（默认提示）')
      sendEmailCode({ email: this.registerForm.email })
        .then(res => {
          if (res.data.success) {
            this.$message.success(res.data.message || '验证码已发送（后端数据覆盖）')
          }
        })
        .catch(() => {
          this.$message.error('发送失败')
        })
    }
  }
}
</script>

<style scoped>
.auth-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
}
.auth-card {
  width: 400px;
}
.switch-text {
  margin-top: 10px;
  text-align: center;
}
.switch-text a {
  color: #409eff;
  cursor: pointer;
}
</style>
