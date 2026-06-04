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
        username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
        password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
        email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }]
      }
    }
  },
  methods: {
    // 前端假数据模拟登录
    handleLogin() {
      this.$refs.loginFormRef.validate(valid => {
        if (valid) {
          if (this.loginForm.username && this.loginForm.password) {
            alert(`模拟登录成功：${this.loginForm.username}`)
            this.$router.push('/home')
          } else {
            alert('请输入账号和密码')
          }
        }
      })
    },
    // 前端假数据模拟注册
    handleRegister() {
      this.$refs.registerFormRef.validate(valid => {
        if (valid) {
          alert(`模拟注册成功：${this.registerForm.username}`)
          this.activeTab = 'login'
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
