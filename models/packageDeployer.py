import jimi

class _packageDeployer(jimi.db._document):
    name = str()
    description = str()
    icon = str()
    playbook_name = str()
    tag = str()
    container = bool()
    container_name = str()

    _dbCollection = jimi.db.db["packageDeployer"]
