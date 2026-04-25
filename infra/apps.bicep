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
param deployApi bool = false
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
var apiContainerAppName = 'ca-func-ai-budget-api'
var chatUiContainerAppName = 'ca-ai-budget-chat-ui'

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  name: identityName
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: existingAcrName
  scope: resourceGroup(existingAcrResourceGroup)
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' existing = {
  name: cosmosAccountName
}

resource aiFoundry 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: aiAccountName
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource defaultWorkspaceIdSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' existing = {
  parent: keyVault
  name: 'DEFAULT-WORKSPACE-ID'
}

resource defaultMaxOutputTokensSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' existing = {
  parent: keyVault
  name: 'DEFAULT-MAX-OUTPUT-TOKENS'
}

resource defaultRequestTimeoutSecondsSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' existing = {
  parent: keyVault
  name: 'DEFAULT-REQUEST-TIMEOUT-SECONDS'
}

resource azureOpenAiDeploymentSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' existing = {
  parent: keyVault
  name: 'AZURE-OPENAI-DEPLOYMENT'
}

resource azureOpenAiApiVersionSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' existing = {
  parent: keyVault
  name: 'AZURE-OPENAI-API-VERSION'
}

resource adminApiKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' existing = {
  parent: keyVault
  name: 'ADMIN-API-KEY'
}

module apiContainerApp 'modules/containerapp-function.bicep' = if (deployApi) {
  name: 'containerapp-function-${uniqueString(containerImage)}'
  params: {
    location: location
    containerAppName: apiContainerAppName
    containerImage: containerImage
    existingContainerAppsEnvironmentName: existingContainerAppsEnvironmentName
    existingContainerAppsEnvironmentResourceGroup: existingContainerAppsEnvironmentResourceGroup
    identityId: identity.id
    identityClientId: identity.properties.clientId
    acrLoginServer: acr.properties.loginServer
    storageAccountName: storage.name
    keyVaultIdentityId: identity.id
    defaultWorkspaceIdSecretUrl: defaultWorkspaceIdSecret.properties.secretUri
    defaultMaxOutputTokensSecretUrl: defaultMaxOutputTokensSecret.properties.secretUri
    defaultRequestTimeoutSecondsSecretUrl: defaultRequestTimeoutSecondsSecret.properties.secretUri
    azureOpenAiDeploymentSecretUrl: azureOpenAiDeploymentSecret.properties.secretUri
    azureOpenAiApiVersionSecretUrl: azureOpenAiApiVersionSecret.properties.secretUri
    adminApiKeySecretUrl: adminApiKeySecret.properties.secretUri
    cosmosEndpoint: cosmos.properties.documentEndpoint
    azureOpenAiEndpoint: aiFoundry.properties.endpoint
    minReplicas: containerAppMinReplicas
    maxReplicas: containerAppMaxReplicas
    tags: tags
  }
}

module chatUiContainerApp 'modules/containerapp-ui.bicep' = if (deployChatUi) {
  name: 'containerapp-chat-ui-${uniqueString(chatUiContainerImage)}'
  params: {
    location: location
    containerAppName: chatUiContainerAppName
    containerImage: chatUiContainerImage
    existingContainerAppsEnvironmentName: existingContainerAppsEnvironmentName
    existingContainerAppsEnvironmentResourceGroup: existingContainerAppsEnvironmentResourceGroup
    identityId: identity.id
    acrLoginServer: acr.properties.loginServer
    minReplicas: containerAppMinReplicas
    maxReplicas: containerAppMaxReplicas
    tags: union(tags, {
      app: 'chat-ui'
      apiBaseUrl: chatUiApiBaseUrl
    })
  }
}

output apiContainerAppName string = apiContainerAppName
output apiContainerAppFqdn string = deployApi ? apiContainerApp!.outputs.fqdn : ''
output chatUiContainerAppName string = chatUiContainerAppName
output chatUiContainerAppFqdn string = deployChatUi ? chatUiContainerApp!.outputs.fqdn : ''
output azureOpenAiDeploymentName string = azureOpenAiDeploymentName
output azureOpenAiModelName string = azureOpenAiModelName
output azureOpenAiModelVersion string = azureOpenAiModelVersion
output azureOpenAiApiVersion string = azureOpenAiApiVersion
output azureOpenAiDeploymentCapacity int = azureOpenAiDeploymentCapacity
output enableCosmosFreeTier bool = enableCosmosFreeTier
output cosmosDatabaseThroughput int = cosmosDatabaseThroughput
output enableKeyVaultPurgeProtection bool = enableKeyVaultPurgeProtection
output defaultWorkspaceId string = defaultWorkspaceId
