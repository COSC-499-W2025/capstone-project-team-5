import json
from data.models.user_config_model import UserConfigModel
from sqlalchemy import Session
from capstone_project_team_5.user_config import UserConfig

def load_user_config(session: Session) -> UserConfig:
    """
    Loads the user configuration from the database into a UserConfig object.
    Returns a default UserConfig if none exists.
    """
    record = session.query(UserConfigModel).first()
    if record:
        return UserConfig(
            consent_given=record.consent_given,
            use_external_services=record.use_external_services,
            external_services=record.external_services,
            default_ignore_patterns=record.default_ignore_patterns
        )
    return UserConfig() # return default if no config record exists

def store_user_config(session: Session, config: UserConfig) -> None:
    """
    Inserts or updates the user configuration record.
    Always maintains a single record (user_config_id = 1).
    """
    record = session.query(UserConfigModel).first()
    if not record:
        record = UserConfigModel(user_config_id=1)
        session.add(record)
    
    record.consent_given = config.consent_given
    record.use_external_services = config.use_external_services
    record.external_services = json.dumps(config.external_services)
    record.default_ignore_patterns = json.dumps(config.default_ignore_patterns)
    
    session.commit()
