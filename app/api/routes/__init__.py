def register_route_modules(api_bp) -> None:
    from app.api.routes.backup import backup_bp
    from app.api.routes.candados import candados_bp
    from app.api.routes.catalogos import catalogos_bp
    from app.api.routes.docentes import docentes_bp
    from app.api.routes.exportaciones import exportaciones_bp
    from app.api.routes.grupos import grupos_bp
    from app.api.routes.horarios import horarios_bp
    from app.api.routes.ia import ia_bp
    from app.api.routes.materias import materias_bp

    api_bp.register_blueprint(catalogos_bp)
    api_bp.register_blueprint(candados_bp)
    api_bp.register_blueprint(grupos_bp)
    api_bp.register_blueprint(materias_bp)
    api_bp.register_blueprint(docentes_bp)
    api_bp.register_blueprint(horarios_bp)
    api_bp.register_blueprint(exportaciones_bp)
    api_bp.register_blueprint(ia_bp)
    api_bp.register_blueprint(backup_bp)