<template>
  <div class="auth-container">
    <!-- 漂浮彩色球体背景 -->
    <div class="floating-spheres">
      <div class="sphere sphere-1"></div>
      <div class="sphere sphere-2"></div>
      <div class="sphere sphere-3"></div>
      <div class="sphere sphere-4"></div>
      <div class="sphere sphere-5"></div>
      <div class="sphere sphere-6"></div>
      <div class="sphere sphere-7"></div>
    </div>

    <!-- 品牌标题 -->
    <div class="brand-header">
      <h1 class="brand-title">EduSpider</h1>
      <p class="brand-desc">智能教育数据采集平台</p>
    </div>

    <el-card class="auth-card">
      <el-tabs v-model="activeTab" stretch>
        <!-- 登录 -->
        <el-tab-pane label="登录" name="login">
          <el-form :model="loginForm" :rules="loginRules" ref="loginFormRef" label-width="80px" class="auth-form">
            <el-form-item label="账号" prop="username">
              <el-input v-model="loginForm.username" placeholder="请输入账号"></el-input>
            </el-form-item>
            <el-form-item label="密码" prop="password">
              <el-input v-model="loginForm.password" type="password" placeholder="请输入密码"></el-input>
            </el-form-item>
            <el-form-item class="btn-center">
              <el-button type="primary" @click="handleLogin">登录</el-button>
            </el-form-item>
            <p class="switch-text">没有账号？<a @click="activeTab='register'">立即注册</a></p>
          </el-form>
        </el-tab-pane>

        <!-- 注册 -->
        <el-tab-pane label="注册" name="register">
          <el-form :model="registerForm" :rules="registerRules" ref="registerFormRef" label-width="80px" class="auth-form">
            <el-form-item label="账号" prop="username">
              <el-input v-model="registerForm.username" placeholder="请输入账号"></el-input>
            </el-form-item>
            <el-form-item label="密码" prop="password">
              <el-input v-model="registerForm.password" type="password" placeholder="请输入密码"></el-input>
            </el-form-item>
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="registerForm.email" placeholder="请输入邮箱"></el-input>
            </el-form-item>
            <div class="btn-center">
              <el-button type="primary" @click="handleSendCode">发送验证码</el-button>
            </div>
            <el-form-item label="验证码" prop="email_code">
              <el-input v-model="registerForm.email_code" placeholder="请输入邮箱验证码"></el-input>
            </el-form-item>
            <el-form-item class="btn-center">
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

    async handleLogin() {
      this.$refs.loginFormRef.validate(async (valid) => {
        if (valid) {
          const loading = this.$loading({
            lock: true,
            text: '登录中...',
            spinner: 'el-icon-loading',
            background: 'rgba(0, 0, 0, 0.7)'
          })
          try {
            const res = await login(this.loginForm)
            if (res.data.code === 200) {
              const { token, user } = res.data.data
              localStorage.setItem('token', token)
              localStorage.setItem('username', user.username)
              localStorage.setItem('email', user.email || '')
              localStorage.setItem('userId', user.id)
              this.$message.success('登录成功')
              this.$router.push('/home')
            } else {
              this.$message.error(res.data.msg || '登录失败')
            }
          } catch (error) {
            console.error('登录错误:', error)
            this.$message.error('登录失败，请检查用户名和密码')
          } finally {
            loading.close()
          }
        }
      })
    },

    async handleRegister() {
      this.$refs.registerFormRef.validate(async (valid) => {
        if (valid) {
          const loading = this.$loading({
            lock: true,
            text: '注册中...',
            spinner: 'el-icon-loading',
            background: 'rgba(0, 0, 0, 0.7)'
          })
          try {
            const res = await register(this.registerForm)
            if (res.data.code === 200) {
              this.$message.success(res.data.msg || '注册成功，请登录')
              this.registerForm = { username: '', password: '', email: '', email_code: '' }
              this.activeTab = 'login'
            } else {
              this.$message.error(res.data.msg || '注册失败')
            }
          } catch (error) {
            console.error('注册错误:', error)
            const msg = error.response?.data?.msg || error.response?.data?.error || '注册失败，请稍后重试'
            this.$message.error(msg)
          } finally {
            loading.close()
          }
        }
      })
    },

    async handleSendCode() {
      if (!this.registerForm.email) {
        this.$message.error('请先输入邮箱')
        return
      }
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      if (!emailRegex.test(this.registerForm.email)) {
        this.$message.error('邮箱格式不正确')
        return
      }
      const loading = this.$loading({
        lock: true,
        text: '发送中...',
        spinner: 'el-icon-loading',
        background: 'rgba(0, 0, 0, 0.7)'
      })
      try {
        const res = await sendEmailCode({ email: this.registerForm.email })
        if (res.data.code === 200) {
          this.$message.success(res.data.msg || '验证码已发送')
          this.registerForm.email_code = '123456'
        } else {
          this.$message.error(res.data.msg || '发送失败')
        }
      } catch (error) {
        console.error('发送验证码错误:', error)
        this.$message.error('发送验证码失败，请稍后重试')
      } finally {
        loading.close()
      }
    }
  }
}
</script>

<style scoped>
/* 全屏背景，固定高度，无滚动条 */
.auth-container {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100vh;
  overflow: hidden;
  background: linear-gradient(135deg, #f5f0ff 0%, #eef3ff 30%, #f8f6ff 60%, #f0f4ff 100%);
}

/* 漂浮球体 */
.floating-spheres {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  pointer-events: none;
}

.sphere {
  position: absolute;
  border-radius: 50%;
  filter: blur(2px);
  animation: floatSphere linear infinite alternate;
}

.sphere-1 {
  width: 120px;
  height: 120px;
  top: 10%;
  left: 15%;
  background: radial-gradient(circle at 30% 30%, rgba(64,158,255,0.7), rgba(64,158,255,0.1));
  box-shadow: 0 0 60px rgba(64,158,255,0.5);
  animation-duration: 18s;
}

.sphere-2 {
  width: 90px;
  height: 90px;
  top: 60%;
  left: 80%;
  background: radial-gradient(circle at 40% 40%, rgba(123,97,255,0.7), rgba(123,97,255,0.1));
  box-shadow: 0 0 50px rgba(123,97,255,0.5);
  animation-duration: 22s;
  animation-delay: -5s;
}

.sphere-3 {
  width: 80px;
  height: 80px;
  top: 80%;
  left: 10%;
  background: radial-gradient(circle at 35% 35%, rgba(255,100,150,0.6), rgba(255,100,150,0.1));
  box-shadow: 0 0 50px rgba(255,100,150,0.4);
  animation-duration: 20s;
  animation-delay: -10s;
}

.sphere-4 {
  width: 110px;
  height: 110px;
  top: 20%;
  left: 70%;
  background: radial-gradient(circle at 40% 40%, rgba(64,200,255,0.65), rgba(64,200,255,0.1));
  box-shadow: 0 0 60px rgba(64,200,255,0.4);
  animation-duration: 25s;
  animation-delay: -3s;
}

.sphere-5 {
  width: 70px;
  height: 70px;
  top: 45%;
  left: 30%;
  background: radial-gradient(circle at 30% 30%, rgba(100,150,255,0.7), rgba(100,150,255,0.1));
  box-shadow: 0 0 45px rgba(100,150,255,0.5);
  animation-duration: 16s;
  animation-delay: -8s;
}

.sphere-6 {
  width: 95px;
  height: 95px;
  top: 75%;
  left: 55%;
  background: radial-gradient(circle at 35% 35%, rgba(180,130,255,0.65), rgba(180,130,255,0.1));
  box-shadow: 0 0 55px rgba(180,130,255,0.4);
  animation-duration: 19s;
  animation-delay: -12s;
}

.sphere-7 {
  width: 85px;
  height: 85px;
  top: 5%;
  left: 50%;
  background: radial-gradient(circle at 40% 40%, rgba(255,130,180,0.6), rgba(255,130,180,0.1));
  box-shadow: 0 0 50px rgba(255,130,180,0.4);
  animation-duration: 21s;
  animation-delay: -15s;
}

@keyframes floatSphere {
  0% {
    transform: translate(0, 0) rotate(0deg) scale(1);
  }
  25% {
    transform: translate(30px, -40px) rotate(10deg) scale(1.15);
  }
  50% {
    transform: translate(-20px, -15px) rotate(-5deg) scale(0.9);
  }
  75% {
    transform: translate(35px, 25px) rotate(8deg) scale(1.1);
  }
  100% {
    transform: translate(-15px, 35px) rotate(-4deg) scale(1);
  }
}

/* 品牌标题 */
.brand-header {
  position: relative;
  z-index: 1;
  text-align: center;
  margin-bottom: 20px;
}

.brand-title {
  font-size: 42px;
  font-weight: 700;
  color: #303133;
  margin: 0;
  letter-spacing: 4px;
  text-shadow: 0 0 20px rgba(64,158,255,0.2);
}

.brand-desc {
  font-size: 16px;
  color: #606266;
  margin-top: 6px;
  font-weight: 300;
}

/* 卡片 */
.auth-card {
  position: relative;
  z-index: 1;
  width: 420px;
  max-width: calc(100vw - 40px);
  background: rgba(255, 255, 255, 0.35);
  backdrop-filter: blur(25px);
  -webkit-backdrop-filter: blur(25px);
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.7);
  box-shadow: 0 15px 40px rgba(64, 158, 255, 0.15);
}

/* 表单内部间距收紧，防止溢出 */
.auth-form .el-form-item {
  margin-bottom: 14px;
}
.auth-form .el-form-item:last-child {
  margin-bottom: 0;
}

/* 按钮居中 */
.btn-center {
  display: flex;
  justify-content: center;
  margin-bottom: 14px;
}
.btn-center .el-button {
  width: 100%;
  max-width: 200px;
}

/* 切换文字 */
.switch-text {
  margin-top: 8px;
  text-align: center;
  color: #666;
}
.switch-text a {
  color: #409eff;
  cursor: pointer;
}
</style>

<!-- 全局样式：彻底消除滚动条 -->
<style>
html,
body {
  margin: 0;
  padding: 0;
  overflow: hidden;
}
</style>