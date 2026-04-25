targetScope = 'resourceGroup'

param location string = 'westeurope'
param projectName string = 'demo-ai-budget-guardrails'
param defaultWorkspaceId string = 'demo-workspace'
param existingContainerAppsEnvironmentName string = 'aca-arca-prod-env'
param existingContainerAppsEnvironmentResourceGroup string = 'rg-arca-prod'
param existingAcrName string = 'arcaprodweuacr'
param existingAcrResourceGroup string = 'rg-arca-prod'
param containerImage string = ''
param chatUiContainerImage string = ''
param deployContainerApp bool = false
param deployChatUi bool = false
param chatUiApiBaseUrl string = 'https://ca-func-ai-budget-api.salmoncliff-ac0e8a07.westeurope.azurecontainerapps.io'
param azureOpenAiDeploymentName string = 'gpt-4o-mini-chat'
param azureOpenAiModelName string = 'gpt-4o-mini'
param azureOpenAiModelVersion string = '2024-07-18'
param azureOpenAiApiVersion string = '2024-10-21'
param azureOpenAiDeploymentCapacity int = 1
param enableCosmosFreeTier bool = true
param cosmosDatabaseThroughput int = 1000
param containerAppMinReplicas int = 0
param containerAppMaxReplicas int = 1
param enableKeyVaultPurgeProtection bool = false
@secure()
param adminApiKey string = ''
param tags object = {
  project: projectName
  environment: 'dev'
}

var suffix = uniqueString(resourceGroup().id, projectName)
var cosmosAccountName = 'cosmos-ai-budget-${suffix}'
var aiAccountName = 'aoai-ai-budget-${suffix}'
var storageAccountName = 'staibudget${suffix}'
var keyVaultName = 'kvaibg${suffix}'
var identityName = 'id-ai-budget-api'
var containerAppName = 'ca-func-ai-budget-api'
var chatUiContainerAppName = 'ca-ai-budget-chat-ui'

module identity 'modules/identity.bicep' = {
  name: 'identity'
  params: {
    location: location
    identityName: identityName
    tags: tags
  }
}

module acr 'modules/acr-existing.bicep' = {
  name: 'acr-existing'
  scope: resourceGroup(existingAcrResourceGroup)
  params: {
    acrName: existingAcrName
    principalId: identity.outputs.principalId
  }
}

module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    location: location
    storageAccountName: storageAccountName
    principalId: identity.outputs.principalId
    tags: tags
  }
}

module cosmos 'modules/cosmos.bicep' = {
  name: 'cosmos'
  params: {
    location: location
    accountName: cosmosAccountName
    databaseName: 'ai-budget-db'
    enableFreeTier: enableCosmosFreeTier
    databaseThroughput: cosmosDatabaseThroughput
    principalId: identity.outputs.principalId
    tags: tags
  }
}

module aiFoundry 'modules/ai-foundry.bicep' = {
  name: 'ai-foundry-openai'
  params: {
    location: location
    accountName: aiAccountName
    deploymentName: azureOpenAiDeploymentName
    modelName: azureOpenAiModelName
    modelVersion: azureOpenAiModelVersion
    deploymentCapacity: azureOpenAiDeploymentCapacity
    principalId: identity.outputs.principalId
    tags: tags
  }
}

module keyVault 'modules/keyvault.bicep' = {
  name: 'keyvault'
  params: {
    location: location
    keyVaultName: keyVaultName
    principalId: identity.outputs.principalId
    enablePurgeProtection: enableKeyVaultPurgeProtection
    appConfigValues: {
      defaultWorkspaceId: defaultWorkspaceId
      defaultMaxOutputTokens: '500'
      defaultRequestTimeoutSeconds: '30'
      azureOpenAiDeployment: azureOpenAiDeploymentName
      azureOpenAiApiVersion: azureOpenAiApiVersion
      adminApiKey: adminApiKey
    }
    tags: tags
  }
}

module containerApp 'modules/containerapp-function.bicep' = if (deployContainerApp) {
  name: 'containerapp-function'
  params: {
    location: location
    containerAppName: containerAppName
    containerImage: containerImage
    existingContainerAppsEnvironmentName: existingContainerAppsEnvironmentName
    existingContainerAppsEnvironmentResourceGroup: existingContainerAppsEnvironmentResourceGroup
    identityId: identity.outputs.id
    identityClientId: identity.outputs.clientId
    acrLoginServer: acr.outputs.loginServer
    storageAccountName: storage.outputs.name
    keyVaultIdentityId: identity.outputs.id
    defaultWorkspaceIdSecretUrl: keyVault.outputs.defaultWorkspaceIdSecretUrl
    defaultMaxOutputTokensSecretUrl: keyVault.outputs.defaultMaxOutputTokensSecretUrl
    defaultRequestTimeoutSecondsSecretUrl: keyVault.outputs.defaultRequestTimeoutSecondsSecretUrl
    azureOpenAiDeploymentSecretUrl: keyVault.outputs.azureOpenAiDeploymentSecretUrl
    azureOpenAiApiVersionSecretUrl: keyVault.outputs.azureOpenAiApiVersionSecretUrl
    adminApiKeySecretUrl: keyVault.outputs.adminApiKeySecretUrl
    cosmosEndpoint: cosmos.outputs.endpoint
    azureOpenAiEndpoint: aiFoundry.outputs.endpoint
    minReplicas: containerAppMinReplicas
    maxReplicas: containerAppMaxReplicas
    tags: tags
  }
}

module chatUiContainerApp 'modules/containerapp-ui.bicep' = if (deployChatUi) {
  name: 'containerapp-chat-ui'
  params: {
    location: location
    containerAppName: chatUiContainerAppName
    containerImage: chatUiContainerImage
    existingContainerAppsEnvironmentName: existingContainerAppsEnvironmentName
    existingContainerAppsEnvironmentResourceGroup: existingContainerAppsEnvironmentResourceGroup
    identityId: identity.outputs.id
    acrLoginServer: acr.outputs.loginServer
    minReplicas: containerAppMinReplicas
    maxReplicas: containerAppMaxReplicas
    tags: union(tags, {
      app: 'chat-ui'
      apiBaseUrl: chatUiApiBaseUrl
    })
  }
}

output acrName string = acr.outputs.name
output acrLoginServer string = acr.outputs.loginServer
output apiIdentityClientId string = identity.outputs.clientId
output keyVaultName string = keyVault.outputs.name
output cosmosEndpoint string = cosmos.outputs.endpoint
output azureOpenAiEndpoint string = aiFoundry.outputs.endpoint
output azureOpenAiDeploymentName string = azureOpenAiDeploymentName
output containerAppName string = containerAppName
output containerAppFqdn string = deployContainerApp ? containerApp!.outputs.fqdn : ''
output chatUiContainerAppName string = chatUiContainerAppName
output chatUiContainerAppFqdn string = deployChatUi ? chatUiContainerApp!.outputs.fqdn : ''
