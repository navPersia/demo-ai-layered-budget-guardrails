param location string
param keyVaultName string
param principalId string
param enablePurgeProtection bool = false
param appConfigValues object
param tags object

var vaultProperties = union({
  tenantId: tenant().tenantId
  sku: {
    family: 'A'
    name: 'standard'
  }
  enableRbacAuthorization: true
  enabledForTemplateDeployment: true
  enableSoftDelete: true
  softDeleteRetentionInDays: 7
  publicNetworkAccess: 'Enabled'
  networkAcls: {
    bypass: 'AzureServices'
    defaultAction: 'Allow'
  }
}, enablePurgeProtection ? {
  enablePurgeProtection: true
} : {})

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: vaultProperties
}

var keyVaultSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

resource secretsUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(vault.id, principalId, keyVaultSecretsUserRoleId)
  scope: vault
  properties: {
    principalId: principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUserRoleId)
  }
}

resource defaultWorkspaceId 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: vault
  name: 'DEFAULT-WORKSPACE-ID'
  properties: {
    value: appConfigValues.defaultWorkspaceId
  }
}

resource defaultMaxOutputTokens 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: vault
  name: 'DEFAULT-MAX-OUTPUT-TOKENS'
  properties: {
    value: appConfigValues.defaultMaxOutputTokens
  }
}

resource defaultRequestTimeoutSeconds 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: vault
  name: 'DEFAULT-REQUEST-TIMEOUT-SECONDS'
  properties: {
    value: appConfigValues.defaultRequestTimeoutSeconds
  }
}

resource azureOpenAiDeployment 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: vault
  name: 'AZURE-OPENAI-DEPLOYMENT'
  properties: {
    value: appConfigValues.azureOpenAiDeployment
  }
}

resource azureOpenAiApiVersion 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: vault
  name: 'AZURE-OPENAI-API-VERSION'
  properties: {
    value: appConfigValues.azureOpenAiApiVersion
  }
}

resource adminApiKey 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: vault
  name: 'ADMIN-API-KEY'
  properties: {
    value: appConfigValues.adminApiKey
  }
}

output id string = vault.id
output name string = vault.name
output vaultUri string = vault.properties.vaultUri
output defaultWorkspaceIdSecretUrl string = defaultWorkspaceId.properties.secretUri
output defaultMaxOutputTokensSecretUrl string = defaultMaxOutputTokens.properties.secretUri
output defaultRequestTimeoutSecondsSecretUrl string = defaultRequestTimeoutSeconds.properties.secretUri
output azureOpenAiDeploymentSecretUrl string = azureOpenAiDeployment.properties.secretUri
output azureOpenAiApiVersionSecretUrl string = azureOpenAiApiVersion.properties.secretUri
output adminApiKeySecretUrl string = adminApiKey.properties.secretUri
