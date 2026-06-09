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
import { login, register } from '../api/auth'

export default {
  name: 'LoginRegisterPage',
  data() {
    return {
      activeTab: 'login',
      loginForm: { username: '', password: '' },
      registerForm: { username: '', password: '', email: '' },
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
        ]
      }
    }
  },
  methods: {
    // 用户名校验：不超过10位
    validateUsername(rule, value, callback) {
      if (value.length > 10) {
        return callback(new Error('用户名不能超过10位'))
      }
      return callback()
    },

    // 密码校验：至少8位，包含字母和数字
    validatePassword(rule, value, callback) {
      const passwordRegex = /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$/
      if (!passwordRegex.test(value)) {
        return callback(new Error('密码必须至少8位，且包含字母和数字'))
      }
      return callback()
    },

    // 邮箱校验：允许所有合法邮箱，包括 hust.edu.cn
    validateEmail(rule, value, callback) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      if (!emailRegex.test(value)) {
        return callback(new Error('邮箱格式不正确'))
      }
      // 如果只允许 hust 邮箱，可以启用下面的逻辑：
      // if (!value.endsWith('@hust.edu.cn')) {
      //   return callback(new Error('必须使用 hust.edu.cn 邮箱'))
      // }
      return callback()
    },

    // 登录接口调用
    handleLogin() {
      this.$refs.loginFormRef.validate(valid => {
        if (valid) {
          login(this.loginForm)
            .then(res => {
              const token = res.data.token
              localStorage.setItem('token', token)
              this.$message.success('登录成功')
              this.$router.push('/home')
            })
            .catch(() => {
              this.$message.error('登录失败')
            })
        }
      })
    },

    // 注册接口调用（假接口）
    handleRegister() {
      this.$refs.registerFormRef.validate(valid => {
        if (valid) {
          register(this.registerForm)
            .then(res => {
              this.$message.success(`注册成功：用户ID ${res.data.userId}`)
              this.activeTab = 'login'
            })
            .catch(() => {
              this.$message.error('注册失败')
            })
        }
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
