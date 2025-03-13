#!/usr/bin/env groovy

import jenkins.model.*
import hudson.security.*
import jenkins.install.*

def instance = Jenkins.getInstance()

// Create default admin user
def hudsonRealm = new HudsonPrivateSecurityRealm(false)
hudsonRealm.createAccount("admin", "admin123")
instance.setSecurityRealm(hudsonRealm)

// Disable security (vulnerability)
def strategy = new hudson.security.AuthorizationStrategy.Unsecured()
instance.setAuthorizationStrategy(strategy)

// Disable setup wizard
instance.setInstallState(InstallState.INITIAL_SETUP_COMPLETED)

instance.save() 