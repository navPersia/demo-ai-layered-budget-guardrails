param location string
param containerAppName string
param containerImage string
param existingContainerAppsEnvironmentName string
param existingContainerAppsEnvironmentResourceGroup string
param identityId string
param acrLoginServer string
param minReplicas int = 0
param maxReplicas int = 1
param tags object

resource existingEnv 'Microsoft.App/managedEnvironments@2024-03-01' existing = {
  name: existingContainerAppsEnvironmentName
  scope: resourceGroup(existingContainerAppsEnvironmentResourceGroup)
}

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: containerAppName
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: existingEnv.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 80
        transport: 'auto'
      }
      registries: [
        {
          server: acrLoginServer
          identity: identityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'chat-ui'
          image: containerImage
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
      }
    }
  }
}

output id string = containerApp.id
output name string = containerApp.name
output fqdn string = containerApp.properties.configuration.ingress.fqdn

