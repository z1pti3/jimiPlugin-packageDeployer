import jimi

class _packageDeployer(jimi.plugin._plugin):
    version = 0.1

    def install(self):
        jimi.model.registerModel("packageDeployer","_packageDeployer","_document","plugins.packageDeployer.models.packageDeployer",True)
        return True

    def uninstall(self):
        jimi.model.deregisterModel("packageDeployer","_packageDeployer","_document","plugins.packageDeployer.models.packageDeployer")
        return True

    def upgrade(self,LatestPluginVersion):
        return True
