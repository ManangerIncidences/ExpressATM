from sqlalchemy.orm import Session
from .models import Alert, SalesRecord, Agency
from .database import SessionLocal
from backend.config import Config
from .agency_matcher import get_agency_matcher
from datetime import datetime, date
from typing import List, Dict
import logging
from .agency_behavior_analyzer import is_agency_unusual, agency_analyzer

logger = logging.getLogger(__name__)

class AlertSystem:
    def __init__(self):
        self.thresholds = Config.ALERT_THRESHOLDS
    
    def _should_skip_agency(self, agency_name: str) -> bool:
        """Determinar si una agencia debe ser omitida basándose en su nombre"""
        if not agency_name:
            return False
            
        agency_name_lower = agency_name.lower()
        
        # Filtros por nombre
        skip_keywords = [
            'suriel',
            'total general'
        ]
        
        for keyword in skip_keywords:
            if keyword in agency_name_lower:
                return True
                
        return False
    
    def _ensure_agency_exists(self, db: Session, agency_code: str, agency_name: str) -> Agency:
        """Asegurar que una agencia existe en la base de datos de forma segura"""
        # Intentar obtener agencia existente primero
        agency = db.query(Agency).filter(Agency.code == agency_code).first()
        if agency:
            return agency
        
        # Si no existe, intentar crear usando INSERT OR IGNORE equivalente
        try:
            # Crear nueva agencia
            agency = Agency(code=agency_code, name=agency_name)
            db.add(agency)
            
            # No hacer flush aquí, dejar que el commit principal maneje la transacción
            return agency
            
        except Exception as e:
            # Si hay cualquier error, hacer rollback y obtener la existente
            logger.warning(f"Conflicto al insertar agencia {agency_code}, obteniendo existente: {e}")
            db.rollback()
            
            # Intentar obtener la agencia que debe existir ahora
            agency = db.query(Agency).filter(Agency.code == agency_code).first()
            if agency:
                return agency
            else:
                # Si aún no existe, re-intentar la creación
                logger.error(f"Error crítico: no se puede crear ni obtener agencia {agency_code}")
                raise Exception(f"No se puede asegurar la existencia de la agencia {agency_code}")
    
    def process_agencies_data(self, agencies_data: List[Dict], db: Session) -> List[Dict]:
        """Procesar datos de agencias y generar alertas"""
        alerts_generated = []
        today = date.today().isoformat()
        matcher = get_agency_matcher()
        
        # Procesar agencias en lotes para mejor manejo de transacciones
        batch_size = 50
        total_agencies = len(agencies_data)
        
        for i in range(0, total_agencies, batch_size):
            batch = agencies_data[i:i + batch_size]
            logger.info(f"Procesando lote {i//batch_size + 1}: {len(batch)} agencias")
            
            try:
                # Procesar lote
                batch_alerts = self._process_agency_batch(batch, db, today, matcher)
                alerts_generated.extend(batch_alerts)
                
                # Commit del lote
                db.commit()
                logger.debug(f"Lote {i//batch_size + 1} procesado exitosamente")
                
            except Exception as e:
                logger.error(f"Error procesando lote {i//batch_size + 1}: {e}")
                db.rollback()
                
                # Intentar procesar agencias individualmente en caso de error
                logger.info("Intentando procesamiento individual...")
                for agency_data in batch:
                    try:
                        individual_alerts = self._process_single_agency(agency_data, db, today, matcher)
                        alerts_generated.extend(individual_alerts)
                        db.commit()
                    except Exception as individual_error:
                        logger.error(f"Error procesando agencia {agency_data.get('agency_code', 'UNKNOWN')}: {individual_error}")
                        db.rollback()
                        continue
        
        return alerts_generated
    
    def _process_agency_batch(self, agencies_batch: List[Dict], db: Session, today: str, matcher) -> List[Dict]:
        """Procesar un lote de agencias"""
        alerts_generated = []
        
        for agency_data in agencies_batch:
            individual_alerts = self._process_single_agency(agency_data, db, today, matcher)
            alerts_generated.extend(individual_alerts)
        
        return alerts_generated
    
    def _process_single_agency(self, agency_data: Dict, db: Session, today: str, matcher) -> List[Dict]:
        """Procesar una sola agencia"""
        agency_code = agency_data["agency_code"]
        agency_name = agency_data["agency_name"]
        lottery_type = agency_data.get("lottery_type", "UNKNOWN")
        
        # 🚫 FILTRO DIRECTO: Omitir agencias SURIEL y Total General por nombre
        if self._should_skip_agency(agency_name):
            logger.info(f"🚫 Omitiendo agencia filtrada: {agency_code} - {agency_name} ({lottery_type})")
            return []
        
        # 🎯 NUEVA FUNCIONALIDAD: Buscar grupo usando el matcher avanzado
        group_info = matcher.find_agency_group(agency_code, agency_name)
        
        if group_info:
            # Enriquecer datos con información del grupo
            agency_data["group_name"] = group_info.get('grupo', 'Sin Grupo')
            agency_data["group_terminal"] = group_info.get('terminal', agency_name)
            logger.debug(f"✅ Grupo encontrado para {agency_code} ({lottery_type}): {group_info['grupo']}")
        else:
            agency_data["group_name"] = "Sin Grupo"
            agency_data["group_terminal"] = agency_name
            logger.warning(f"⚠️ No se encontró grupo para {agency_code} - {agency_name} ({lottery_type})")
        
        # Guardar registro de ventas actual CON TIPO DE LOTERÍA
        sales_record = SalesRecord(
            agency_code=agency_code,
            agency_name=agency_data["agency_name"],
            sales=agency_data["sales"],
            prizes=agency_data["prizes"],
            prizes_paid=agency_data["prizes_paid"],
            balance=agency_data["balance"],
            lottery_type=lottery_type,  # ✨ NUEVO CAMPO
            capture_day=today,
            iteration_time=agency_data["capture_time"]
        )
        db.add(sales_record)
        
        # Crear o actualizar agencia de forma segura
        self._ensure_agency_exists(db, agency_code, agency_data["agency_name"])
        
        # Verificar alertas POR TIPO DE LOTERÍA (independientes)
        new_alerts = self._check_alerts(agency_data, db, today, lottery_type)
        
        return new_alerts
    
    def _check_alerts(self, agency_data: Dict, db: Session, today: str, lottery_type: str) -> List[Dict]:
        """Verificar y generar alertas para una agencia EN UNA LOTERÍA ESPECÍFICA"""
        alerts = []
        agency_code = agency_data["agency_code"]
        # Omitir alertas si la agencia ya tiene una alerta reportada hoy
        reported_alert = db.query(Alert).filter(
            Alert.agency_code == agency_code,
            Alert.alert_day == today,
            Alert.is_reported == True
        ).first()
        if reported_alert:
            logger.debug(f"🔕 Se omiten alertas para {agency_code} ya reportado hoy")
            return []
        
        logger.debug(f"🔍 Verificando alertas para {agency_code} en {lottery_type}")
        
        # 1. Alerta por umbral (Balance >= 6000 o Ventas >= 20000)
        threshold_alert = self._check_threshold_alert(agency_data, db, today, lottery_type)
        if threshold_alert:
            alerts.append(threshold_alert)
        
        # 2. Alerta por variación de crecimiento (> 1500 entre iteraciones)
        growth_alert = self._check_growth_variation_alert(agency_data, db, today, lottery_type)
        if growth_alert:
            alerts.append(growth_alert)
        
        # 3. Alerta por crecimiento sostenido (> 500 por iteración)
        sustained_alert = self._check_sustained_growth_alert(agency_data, db, today, lottery_type)
        if sustained_alert:
            alerts.append(sustained_alert)
        
        return alerts
    
    def _check_threshold_alert(self, agency_data: Dict, db: Session, today: str, lottery_type: str) -> Dict:
        """Verificar alerta por umbral EN UNA LOTERÍA ESPECÍFICA"""
        balance = agency_data["balance"]
        sales = agency_data["sales"]
        agency_code = agency_data["agency_code"]
        balance_exceeded = balance >= self.thresholds["balance_threshold"]
        sales_exceeded = sales >= self.thresholds["sales_threshold"]
        if balance_exceeded or sales_exceeded:
            existing_alert = db.query(Alert).filter(
                Alert.agency_code == agency_code,
                Alert.alert_type == "threshold",
                Alert.lottery_type == lottery_type,
                Alert.alert_day == today
            ).first()
            if existing_alert:
                if not existing_alert.is_reported:
                    existing_alert.current_sales = sales
                    existing_alert.current_balance = balance
                    existing_alert.alert_message = f"Umbral superado en {lottery_type} - Balance: ${balance:,.2f} (>= ${self.thresholds['balance_threshold']:,.2f}) Ventas: ${sales:,.2f} (>= ${self.thresholds['sales_threshold']:,.2f})"
                    db.add(existing_alert)
                # Si ya fue reportada, no hacer nada
                return None
            normality_analysis = is_agency_unusual(agency_code, sales, lottery_type)
            growth_analysis = agency_analyzer.analyze_growth_normality(agency_code, lottery_type)
            reasons = []
            if balance_exceeded:
                reasons.append(f"Balance: ${balance:,.2f} (>= ${self.thresholds['balance_threshold']:,.2f})")
            if sales_exceeded:
                reasons.append(f"Ventas: ${sales:,.2f} (>= ${self.thresholds['sales_threshold']:,.2f})")
            base_message = f"Umbral superado en {lottery_type} - {' y '.join(reasons)}"
            enhanced_message = f"{base_message}\n🔍 NORMALIDAD: {normality_analysis}\n📈 CRECIMIENTO: {growth_analysis}"
            alert = Alert(
                agency_code=agency_code,
                agency_name=agency_data["agency_name"],
                alert_type="threshold",
                alert_message=enhanced_message,
                lottery_type=lottery_type,
                current_sales=sales,
                current_balance=balance,
                alert_day=today
            )
            db.add(alert)
            return {
                "type": "threshold",
                "agency_code": agency_code,
                "agency_name": agency_data["agency_name"],
                "lottery_type": lottery_type,
                "message": enhanced_message,
                "normality_analysis": normality_analysis,
                "growth_analysis": growth_analysis,
                "balance": balance,
                "sales": sales
            }
        return None
    
    def _check_growth_variation_alert(self, agency_data: Dict, db: Session, today: str, lottery_type: str) -> Dict:
        """Verificar alerta por variación de crecimiento EN UNA LOTERÍA ESPECÍFICA"""
        agency_code = agency_data["agency_code"]
        current_sales = agency_data["sales"]
        previous_record = db.query(SalesRecord).filter(
            SalesRecord.agency_code == agency_code,
            SalesRecord.lottery_type == lottery_type,
            SalesRecord.capture_day == today
        ).order_by(SalesRecord.iteration_time.desc()).offset(1).first()
        if previous_record:
            sales_variation = current_sales - previous_record.sales
            if sales_variation >= self.thresholds["growth_variation"]:
                existing_alert = db.query(Alert).filter(
                    Alert.agency_code == agency_code,
                    Alert.alert_type == "growth_variation",
                    Alert.lottery_type == lottery_type,
                    Alert.alert_day == today
                ).first()
                if existing_alert:
                    if not existing_alert.is_reported:
                        existing_alert.current_sales = current_sales
                        existing_alert.current_balance = agency_data["balance"]
                        existing_alert.previous_sales = previous_record.sales
                        existing_alert.growth_amount = sales_variation
                        existing_alert.alert_message = f"Crecimiento significativo en {lottery_type}: +${sales_variation:,.2f} desde última iteración (${previous_record.sales:,.2f} → ${current_sales:,.2f})"
                        db.add(existing_alert)
                    return None
                message = f"Crecimiento significativo en {lottery_type}: +${sales_variation:,.2f} desde última iteración (${previous_record.sales:,.2f} → ${current_sales:,.2f})"
                alert = Alert(
                    agency_code=agency_code,
                    agency_name=agency_data["agency_name"],
                    alert_type="growth_variation",
                    alert_message=message,
                    lottery_type=lottery_type,
                    current_sales=current_sales,
                    current_balance=agency_data["balance"],
                    previous_sales=previous_record.sales,
                    growth_amount=sales_variation,
                    alert_day=today
                )
                db.add(alert)
                return {
                    "type": "growth_variation",
                    "agency_code": agency_code,
                    "agency_name": agency_data["agency_name"],
                    "lottery_type": lottery_type,
                    "message": message,
                    "growth": sales_variation,
                    "previous_sales": previous_record.sales,
                    "current_sales": current_sales
                }
        return None
    
    def _check_sustained_growth_alert(self, agency_data: Dict, db: Session, today: str, lottery_type: str) -> Dict:
        """Verificar alerta por crecimiento sostenido EN UNA LOTERÍA ESPECÍFICA"""
        agency_code = agency_data["agency_code"]
        recent_records = db.query(SalesRecord).filter(
            SalesRecord.agency_code == agency_code,
            SalesRecord.lottery_type == lottery_type,
            SalesRecord.capture_day == today
        ).order_by(SalesRecord.iteration_time.desc()).limit(3).all()
        if len(recent_records) >= 3:
            growth_increments = []
            for i in range(len(recent_records) - 1):
                current = recent_records[i].sales
                previous = recent_records[i + 1].sales
                increment = current - previous
                growth_increments.append(increment)
            sustained_growth = all(increment >= self.thresholds["sustained_growth"] for increment in growth_increments)
            if sustained_growth:
                existing_alert = db.query(Alert).filter(
                    Alert.agency_code == agency_code,
                    Alert.alert_type == "sustained_growth",
                    Alert.lottery_type == lottery_type,
                    Alert.alert_day == today
                ).first()
                if existing_alert:
                    if not existing_alert.is_reported:
                        existing_alert.current_sales = recent_records[0].sales
                        existing_alert.current_balance = agency_data["balance"]
                        existing_alert.growth_amount = sum(growth_increments)
                        existing_alert.alert_message = f"Crecimiento sostenido en {lottery_type}: incrementos de {growth_increments} (Total: +${sum(growth_increments):,.2f})"
                        db.add(existing_alert)
                    return None
                total_growth = sum(growth_increments)
                message = f"Crecimiento sostenido en {lottery_type}: incrementos de {growth_increments} (Total: +${total_growth:,.2f})"
                alert = Alert(
                    agency_code=agency_code,
                    agency_name=agency_data["agency_name"],
                    alert_type="sustained_growth",
                    alert_message=message,
                    lottery_type=lottery_type,
                    current_sales=recent_records[0].sales,
                    current_balance=agency_data["balance"],
                    growth_amount=total_growth,
                    alert_day=today
                )
                db.add(alert)
                return {
                    "type": "sustained_growth",
                    "agency_code": agency_code,
                    "agency_name": agency_data["agency_name"],
                    "lottery_type": lottery_type,
                    "message": message,
                    "growth_increments": growth_increments,
                    "total_growth": total_growth
                }
        return None
    
    def get_pending_alerts(self, db: Session, today: str = None) -> List[Alert]:
        """Obtener alertas pendientes (no reportadas) del día"""
        if not today:
            today = date.today().isoformat()
        
        return db.query(Alert).filter(
            Alert.alert_day == today,
            Alert.is_reported == False
        ).order_by(Alert.created_at.desc()).all()
    
    def mark_alert_as_reported(self, alert_id: int, db: Session) -> bool:
        """Marcar una alerta como reportada"""
        try:
            alert = db.query(Alert).filter(Alert.id == alert_id).first()
            if alert:
                alert.is_reported = True
                alert.reported_at = datetime.now()
                db.commit()
                logger.info(f"Alerta {alert_id} marcada como reportada")
                return True
            return False
        except Exception as e:
            logger.error(f"Error marcando alerta como reportada: {str(e)}")
            return False
    
    def get_agency_growth_history(self, agency_code: str, db: Session, days: int = 7) -> Dict:
        """Obtener historial de crecimiento de una agencia"""
        from datetime import timedelta
        
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        records = db.query(SalesRecord).filter(
            SalesRecord.agency_code == agency_code,
            SalesRecord.capture_day >= start_date.isoformat(),
            SalesRecord.capture_day <= end_date.isoformat()
        ).order_by(SalesRecord.capture_day, SalesRecord.iteration_time).all()
        
        # Agrupar por día y calcular promedios
        daily_data = {}
        for record in records:
            day = record.capture_day
            if day not in daily_data:
                daily_data[day] = []
            daily_data[day].append({
                "sales": record.sales,
                "balance": record.balance,
                "time": record.iteration_time
            })
        
        # Calcular estadísticas diarias
        growth_history = []
        previous_avg_sales = None
        
        for day, day_records in sorted(daily_data.items()):
            avg_sales = sum(r["sales"] for r in day_records) / len(day_records)
            avg_balance = sum(r["balance"] for r in day_records) / len(day_records)
            
            daily_growth = 0
            if previous_avg_sales is not None:
                daily_growth = avg_sales - previous_avg_sales
            
            growth_history.append({
                "date": day,
                "avg_sales": avg_sales,
                "avg_balance": avg_balance,
                "daily_growth": daily_growth,
                "iterations": len(day_records)
            })
            
            previous_avg_sales = avg_sales
        
        return {
            "agency_code": agency_code,
            "period_days": days,
            "growth_history": growth_history
        }