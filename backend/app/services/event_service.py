"""
Event management service with comprehensive business logic
"""
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text
from sqlalchemy.exc import IntegrityError

from app.models.event import Event, EventStatus, EventType, EventVisibility
from app.models.user import User
from app.schemas.event import (
    EventCreate, EventUpdate, EventStatusUpdate, EventResponse,
    EventWizardStep1, EventWizardStep2, EventWizardStep3, 
    EventWizardStep4, EventWizardStep5, EventWizardStep6,
    ScheduleItem, Room, ConflictDetection, WaitlistEntry, WaitlistStats
)
from app.services.base_tenant_service import TenantScopedService
from app.core.database_utils import TenantManager


class EventService:
    """Event management service with full lifecycle support"""
    
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.tenant_manager = TenantManager(db, tenant_id)
    
    # Basic CRUD operations
    
    async def create(self, event_dict: Dict[str, Any]) -> Event:
        """Create event"""
        # Add tenant_id to event data
        event_dict['tenant_id'] = self.tenant_id
        
        event = Event(**event_dict)
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event
    
    async def get(self, event_id: str) -> Optional[Event]:
        """Get event by ID"""
        return self.db.query(Event).filter(
            and_(
                Event.id == event_id,
                Event.tenant_id == self.tenant_id,
                Event.deleted_at.is_(None)
            )
        ).first()
    
    async def update(self, event_id: str, update_dict: Dict[str, Any]) -> Event:
        """Update event"""
        event = await self.get(event_id)
        if not event:
            raise ValueError("Event not found")
        
        for key, value in update_dict.items():
            if hasattr(event, key):
                setattr(event, key, value)
        
        self.db.commit()
        self.db.refresh(event)
        return event
    
    async def delete(self, event_id: str) -> bool:
        """Soft delete event"""
        event = await self.get(event_id)
        if not event:
            return False
        
        event.deleted_at = datetime.utcnow()
        self.db.commit()
        return True
    
    # Core CRUD operations
    
    async def create_event(self, event_data: EventCreate, creator_id: str) -> Event:
        """Create a new event with full validation"""
        # Check slug uniqueness within tenant
        existing = await self.get_by_slug(event_data.slug)
        if existing:
            raise ValueError(f"Event with slug '{event_data.slug}' already exists")
        
        # Create event data dictionary
        event_dict = event_data.dict(exclude_unset=True, exclude={
            'venue', 'virtual', 'branding', 'contact', 'registration',
            'team_formation', 'submission', 'judging', 'hardware', 'prizes'
        })
        
        # Handle nested configuration objects
        if event_data.venue:
            venue_data = event_data.venue.dict(exclude_unset=True)
            event_dict.update({
                'venue_name': venue_data.get('name'),
                'venue_address': venue_data.get('address'),
                'venue_city': venue_data.get('city'),
                'venue_country': venue_data.get('country'),
                'venue_data': venue_data.get('data', {})
            })
        
        if event_data.virtual:
            virtual_data = event_data.virtual.dict(exclude_unset=True)
            event_dict.update({
                'virtual_platform': virtual_data.get('platform'),
                'virtual_link': virtual_data.get('link'),
                'virtual_config': virtual_data.get('config', {})
            })
        
        if event_data.branding:
            branding_data = event_data.branding.dict(exclude_unset=True)
            event_dict.update({
                'logo_url': branding_data.get('logo_url'),
                'banner_url': branding_data.get('banner_url'),
                'primary_color': branding_data.get('primary_color'),
                'secondary_color': branding_data.get('secondary_color')
            })
        
        if event_data.contact:
            contact_data = event_data.contact.dict(exclude_unset=True)
            event_dict.update({
                'contact_email': contact_data.get('contact_email'),
                'support_email': contact_data.get('support_email'),
                'website_url': contact_data.get('website_url'),
                'social_links': contact_data.get('social_links', {}),
                'hashtags': contact_data.get('hashtags', [])
            })
        
        if event_data.registration:
            reg_data = event_data.registration.dict(exclude_unset=True)
            event_dict.update({
                'requires_approval': reg_data.get('requires_approval', False),
                'requires_payment': reg_data.get('requires_payment', False),
                'registration_fee': reg_data.get('registration_fee'),
                'registration_config': reg_data.get('config', {})
            })
        
        if event_data.team_formation:
            team_data = event_data.team_formation.dict(exclude_unset=True)
            event_dict.update({
                'team_formation_enabled': team_data.get('enabled', True),
                'allow_team_creation': team_data.get('allow_team_creation', True),
                'allow_solo_participation': team_data.get('allow_solo_participation', False),
                'skills_matching_enabled': team_data.get('skills_matching_enabled', True)
            })
        
        if event_data.submission:
            sub_data = event_data.submission.dict(exclude_unset=True)
            event_dict.update({
                'required_submission_fields': sub_data.get('required_fields', []),
                'max_file_size_mb': sub_data.get('max_file_size_mb', 100),
                'allowed_file_types': sub_data.get('allowed_file_types', []),
                'submission_config': sub_data.get('config', {})
            })
        
        if event_data.judging:
            judge_data = event_data.judging.dict(exclude_unset=True)
            event_dict.update({
                'public_voting_enabled': judge_data.get('public_voting_enabled', False),
                'peer_voting_enabled': judge_data.get('peer_voting_enabled', False),
                'judging_config': judge_data.get('config', {})
            })
        
        if event_data.hardware:
            hw_data = event_data.hardware.dict(exclude_unset=True)
            event_dict.update({
                'provides_hardware': hw_data.get('provides_hardware', False),
                'hardware_list': hw_data.get('hardware_list', {})
            })
        
        if event_data.prizes:
            prize_data = event_data.prizes.dict(exclude_unset=True)
            event_dict.update({
                'total_prize_pool': prize_data.get('total_prize_pool'),
                'prizes_config': prize_data.get('prizes_config', {})
            })
        
        # Create the event
        event = await self.create(event_dict)
        
        # Log event creation
        await self._log_event_action(event.id, "created", creator_id, {"creator": creator_id})
        
        return event
    
    async def get_by_slug(self, slug: str) -> Optional[Event]:
        """Get event by slug within tenant"""
        return self.db.query(Event).filter(
            and_(
                Event.tenant_id == self.tenant_id,
                Event.slug == slug,
                Event.deleted_at.is_(None)
            )
        ).first()
    
    async def get_events_list(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[EventStatus] = None,
        event_type: Optional[EventType] = None,
        visibility: Optional[EventVisibility] = None,
        search: Optional[str] = None,
        upcoming_only: bool = False,
        published_only: bool = False
    ) -> Tuple[List[Event], int]:
        """Get paginated list of events with filtering"""
        query = self.db.query(Event).filter(
            and_(
                Event.tenant_id == self.tenant_id,
                Event.deleted_at.is_(None)
            )
        )
        
        # Apply filters
        if status:
            query = query.filter(Event.status == status.value)
        
        if event_type:
            query = query.filter(Event.event_type == event_type.value)
        
        if visibility:
            query = query.filter(Event.visibility == visibility.value)
        
        if search:
            search_filter = or_(
                Event.name.ilike(f"%{search}%"),
                Event.description.ilike(f"%{search}%"),
                Event.short_description.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        
        if upcoming_only:
            query = query.filter(Event.start_at > datetime.utcnow())
        
        if published_only:
            query = query.filter(Event.status != EventStatus.DRAFT.value)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        events = query.order_by(Event.start_at.desc()).offset(skip).limit(limit).all()
        
        return events, total
    
    async def update_event(self, event_id: str, update_data: EventUpdate, updater_id: str) -> Event:
        """Update event with validation"""
        event = await self.get(event_id)
        if not event:
            raise ValueError("Event not found")
        
        # Validate status transitions
        if hasattr(update_data, 'status') and update_data.status:
            await self._validate_status_transition(event, update_data.status)
        
        # Handle nested updates similar to create
        update_dict = update_data.dict(exclude_unset=True, exclude_none=True)
        
        # Update the event
        updated_event = await self.update(event_id, update_dict)
        
        # Log the update
        await self._log_event_action(event_id, "updated", updater_id, update_dict)
        
        return updated_event
    
    async def update_event_status(
        self, 
        event_id: str, 
        status_update: EventStatusUpdate, 
        updater_id: str
    ) -> Event:
        """Update event status with validation and logging"""
        event = await self.get(event_id)
        if not event:
            raise ValueError("Event not found")
        
        old_status = event.status
        new_status = status_update.status
        
        # Validate status transition
        await self._validate_status_transition(event, new_status)
        
        # Update status
        event.status = new_status.value
        self.db.commit()
        self.db.refresh(event)
        
        # Log status change
        await self._log_event_action(
            event_id, 
            "status_changed", 
            updater_id,
            {
                "old_status": old_status,
                "new_status": new_status.value,
                "reason": status_update.reason
            }
        )
        
        return event
    
    # Event lifecycle management
    
    async def publish_event(self, event_id: str, publisher_id: str) -> Event:
        """Publish an event (move from DRAFT to PUBLISHED)"""
        event = await self.get(event_id)
        if not event:
            raise ValueError("Event not found")
        
        if event.status != EventStatus.DRAFT.value:
            raise ValueError("Only draft events can be published")
        
        # Validate event is ready for publishing
        validation_errors = await self._validate_event_for_publishing(event)
        if validation_errors:
            raise ValueError(f"Event validation failed: {', '.join(validation_errors)}")
        
        # Update status to published
        await self.update_event_status(
            event_id,
            EventStatusUpdate(status=EventStatus.PUBLISHED, reason="Event published"),
            publisher_id
        )
        
        return await self.get(event_id)
    
    async def open_registration(self, event_id: str, opener_id: str) -> Event:
        """Open event registration"""
        return await self.update_event_status(
            event_id,
            EventStatusUpdate(status=EventStatus.REGISTRATION_OPEN, reason="Registration opened"),
            opener_id
        )
    
    async def close_registration(self, event_id: str, closer_id: str) -> Event:
        """Close event registration"""
        return await self.update_event_status(
            event_id,
            EventStatusUpdate(status=EventStatus.REGISTRATION_CLOSED, reason="Registration closed"),
            closer_id
        )
    
    async def start_event(self, event_id: str, starter_id: str) -> Event:
        """Start event (move to IN_PROGRESS)"""
        return await self.update_event_status(
            event_id,
            EventStatusUpdate(status=EventStatus.IN_PROGRESS, reason="Event started"),
            starter_id
        )
    
    async def complete_event(self, event_id: str, completer_id: str) -> Event:
        """Complete event"""
        return await self.update_event_status(
            event_id,
            EventStatusUpdate(status=EventStatus.COMPLETED, reason="Event completed"),
            completer_id
        )
    
    async def cancel_event(self, event_id: str, canceller_id: str, reason: str) -> Event:
        """Cancel event"""
        return await self.update_event_status(
            event_id,
            EventStatusUpdate(status=EventStatus.CANCELLED, reason=reason),
            canceller_id
        )
    
    # Event wizard functionality
    
    async def create_event_wizard_step1(self, step_data: EventWizardStep1, creator_id: str) -> Dict[str, Any]:
        """Process event creation wizard step 1"""
        # Validate slug uniqueness
        existing = await self.get_by_slug(step_data.slug)
        if existing:
            return {"success": False, "error": f"Event slug '{step_data.slug}' already exists"}
        
        # Create draft event with minimal data
        event_data = EventCreate(
            name=step_data.name,
            slug=step_data.slug,
            description=step_data.description,
            short_description=step_data.short_description,
            event_type=step_data.event_type,
            start_at=datetime.utcnow() + timedelta(days=30),  # Placeholder
            end_at=datetime.utcnow() + timedelta(days=31),    # Placeholder
            status=EventStatus.DRAFT
        )
        
        event = await self.create_event(event_data, creator_id)
        
        return {
            "success": True,
            "event_id": str(event.id),
            "next_step": 2,
            "data": {
                "name": event.name,
                "slug": event.slug,
                "event_type": event.event_type
            }
        }
    
    async def update_event_wizard_step2(
        self, 
        event_id: str, 
        step_data: EventWizardStep2,
        updater_id: str
    ) -> Dict[str, Any]:
        """Process event creation wizard step 2"""
        update_data = EventUpdate(
            start_at=step_data.start_at,
            end_at=step_data.end_at,
            registration_start_at=step_data.registration_start_at,
            registration_end_at=step_data.registration_end_at
        )
        
        try:
            await self.update_event(event_id, update_data, updater_id)
            return {"success": True, "next_step": 3}
        except ValueError as e:
            return {"success": False, "error": str(e)}
    
    async def update_event_wizard_step3(
        self, 
        event_id: str, 
        step_data: EventWizardStep3,
        updater_id: str
    ) -> Dict[str, Any]:
        """Process event creation wizard step 3"""
        update_data = EventUpdate(
            venue=step_data.venue,
            virtual=step_data.virtual
        )
        
        try:
            await self.update_event(event_id, update_data, updater_id)
            return {"success": True, "next_step": 4}
        except ValueError as e:
            return {"success": False, "error": str(e)}
    
    async def update_event_wizard_step4(
        self, 
        event_id: str, 
        step_data: EventWizardStep4,
        updater_id: str
    ) -> Dict[str, Any]:
        """Process event creation wizard step 4"""
        update_data = EventUpdate(
            capacity=step_data.capacity,
            min_team_size=step_data.min_team_size,
            max_team_size=step_data.max_team_size,
            max_teams=step_data.max_teams,
            team_formation=step_data.team_formation
        )
        
        try:
            await self.update_event(event_id, update_data, updater_id)
            return {"success": True, "next_step": 5}
        except ValueError as e:
            return {"success": False, "error": str(e)}
    
    async def update_event_wizard_step5(
        self, 
        event_id: str, 
        step_data: EventWizardStep5,
        updater_id: str
    ) -> Dict[str, Any]:
        """Process event creation wizard step 5"""
        update_data = EventUpdate(
            registration=step_data.registration,
            submission=step_data.submission,
            team_formation_start_at=step_data.team_formation_start_at,
            team_formation_end_at=step_data.team_formation_end_at,
            submission_start_at=step_data.submission_start_at,
            submission_end_at=step_data.submission_end_at
        )
        
        try:
            await self.update_event(event_id, update_data, updater_id)
            return {"success": True, "next_step": 6}
        except ValueError as e:
            return {"success": False, "error": str(e)}
    
    async def update_event_wizard_step6(
        self, 
        event_id: str, 
        step_data: EventWizardStep6,
        updater_id: str
    ) -> Dict[str, Any]:
        """Process event creation wizard step 6 (final)"""
        update_data = EventUpdate(
            judging_start_at=step_data.judging_start_at,
            judging_end_at=step_data.judging_end_at,
            judging=step_data.judging,
            hardware=step_data.hardware,
            prizes=step_data.prizes,
            branding=step_data.branding,
            contact=step_data.contact
        )
        
        try:
            event = await self.update_event(event_id, update_data, updater_id)
            
            # Check if event is ready for publishing
            validation_errors = await self._validate_event_for_publishing(event)
            can_publish = len(validation_errors) == 0
            
            return {
                "success": True,
                "completed": True,
                "can_publish": can_publish,
                "validation_errors": validation_errors if not can_publish else []
            }
        except ValueError as e:
            return {"success": False, "error": str(e)}
    
    # Schedule management
    
    async def get_event_schedule(self, event_id: str) -> List[ScheduleItem]:
        """Get event schedule items"""
        event = await self.get(event_id)
        if not event:
            raise ValueError("Event not found")
        
        # Get schedule from custom_fields or dedicated schedule table
        schedule_data = event.custom_fields.get('schedule', [])
        return [ScheduleItem(**item) for item in schedule_data]
    
    async def add_schedule_item(
        self, 
        event_id: str, 
        schedule_item: ScheduleItem,
        creator_id: str
    ) -> ScheduleItem:
        """Add schedule item with conflict detection"""
        event = await self.get(event_id)
        if not event:
            raise ValueError("Event not found")
        
        # Check for conflicts
        conflicts = await self.detect_schedule_conflicts(event_id, schedule_item)
        if conflicts.has_conflicts:
            raise ValueError(f"Schedule conflicts detected: {conflicts.conflicts}")
        
        # Add to schedule
        schedule_data = event.custom_fields.get('schedule', [])
        
        # Generate ID if not provided
        if not schedule_item.id:
            schedule_item.id = f"schedule_{len(schedule_data) + 1}_{int(datetime.utcnow().timestamp())}"
        
        schedule_data.append(schedule_item.dict())
        
        # Update event
        await self.update_event(
            event_id,
            EventUpdate(custom_fields={**event.custom_fields, 'schedule': schedule_data}),
            creator_id
        )
        
        return schedule_item
    
    async def detect_schedule_conflicts(
        self, 
        event_id: str, 
        new_item: ScheduleItem
    ) -> ConflictDetection:
        """Detect schedule conflicts for a new item"""
        current_schedule = await self.get_event_schedule(event_id)
        
        conflicts = []
        suggestions = []
        
        for existing_item in current_schedule:
            # Check time overlap
            if (new_item.start_at < existing_item.end_at and 
                new_item.end_at > existing_item.start_at):
                
                # Check if it's the same room/location
                if (new_item.room_id and existing_item.room_id and 
                    new_item.room_id == existing_item.room_id):
                    conflicts.append({
                        "type": "room_conflict",
                        "item_id": existing_item.id,
                        "item_title": existing_item.title,
                        "message": f"Room conflict with '{existing_item.title}'"
                    })
                    suggestions.append(f"Consider using a different room or adjusting timing")
                
                # Check organizer conflicts
                if (new_item.organizer and existing_item.organizer and 
                    new_item.organizer == existing_item.organizer):
                    conflicts.append({
                        "type": "organizer_conflict",
                        "item_id": existing_item.id,
                        "item_title": existing_item.title,
                        "message": f"Organizer conflict with '{existing_item.title}'"
                    })
                    suggestions.append(f"Assign different organizer or adjust timing")
        
        return ConflictDetection(
            has_conflicts=len(conflicts) > 0,
            conflicts=conflicts,
            suggestions=suggestions
        )
    
    # Room and resource management
    
    async def get_event_rooms(self, event_id: str) -> List[Room]:
        """Get event rooms/spaces"""
        event = await self.get(event_id)
        if not event:
            raise ValueError("Event not found")
        
        rooms_data = event.custom_fields.get('rooms', [])
        return [Room(**room) for room in rooms_data]
    
    async def add_room(self, event_id: str, room: Room, creator_id: str) -> Room:
        """Add room to event"""
        event = await self.get(event_id)
        if not event:
            raise ValueError("Event not found")
        
        rooms_data = event.custom_fields.get('rooms', [])
        
        # Generate ID if not provided
        if not room.id:
            room.id = f"room_{len(rooms_data) + 1}_{int(datetime.utcnow().timestamp())}"
        
        rooms_data.append(room.dict())
        
        # Update event
        await self.update_event(
            event_id,
            EventUpdate(custom_fields={**event.custom_fields, 'rooms': rooms_data}),
            creator_id
        )
        
        return room
    
    async def check_room_availability(
        self, 
        event_id: str, 
        room_id: str, 
        start_at: datetime, 
        end_at: datetime
    ) -> bool:
        """Check if room is available for given time period"""
        schedule = await self.get_event_schedule(event_id)
        
        for item in schedule:
            if (item.room_id == room_id and 
                item.start_at < end_at and 
                item.end_at > start_at):
                return False
        
        return True
    
    # Capacity and waitlist management
    
    async def get_capacity_info(self, event_id: str) -> Dict[str, Any]:
        """Get detailed capacity information"""
        event = await self.get(event_id)
        if not event:
            raise ValueError("Event not found")
        
        return {
            "capacity": event.capacity,
            "registered": event.registered_count,
            "checked_in": event.checked_in_count,
            "remaining": event.capacity_remaining(),
            "is_full": event.is_at_capacity(),
            "utilization_rate": (event.registered_count / event.capacity * 100) if event.capacity else 0,
            "checkin_rate": (event.checked_in_count / event.registered_count * 100) if event.registered_count else 0
        }
    
    async def add_to_waitlist(self, event_id: str, user_id: str) -> WaitlistEntry:
        """Add user to event waitlist"""
        event = await self.get(event_id)
        if not event:
            raise ValueError("Event not found")
        
        if not event.is_at_capacity():
            raise ValueError("Event is not at capacity, no waitlist needed")
        
        # Get current waitlist
        waitlist_data = event.custom_fields.get('waitlist', [])
        
        # Check if user already on waitlist
        for entry in waitlist_data:
            if entry['user_id'] == user_id:
                raise ValueError("User already on waitlist")
        
        # Create waitlist entry
        position = len(waitlist_data) + 1
        entry = WaitlistEntry(
            id=f"waitlist_{len(waitlist_data) + 1}_{int(datetime.utcnow().timestamp())}",
            user_id=user_id,
            position=position,
            registered_at=datetime.utcnow(),
            status="waiting"
        )
        
        waitlist_data.append(entry.dict())
        
        # Update event
        await self.update_event(
            event_id,
            EventUpdate(custom_fields={**event.custom_fields, 'waitlist': waitlist_data}),
            "system"
        )
        
        return entry
    
    async def process_waitlist(self, event_id: str, spots_available: int = 1) -> List[WaitlistEntry]:
        """Process waitlist when spots become available"""
        event = await self.get(event_id)
        if not event:
            raise ValueError("Event not found")
        
        waitlist_data = event.custom_fields.get('waitlist', [])
        waiting_entries = [entry for entry in waitlist_data if entry['status'] == 'waiting']
        
        # Sort by position
        waiting_entries.sort(key=lambda x: x['position'])
        
        notified_entries = []
        
        for i in range(min(spots_available, len(waiting_entries))):
            entry = waiting_entries[i]
            entry['status'] = 'notified'
            entry['notified_at'] = datetime.utcnow().isoformat()
            entry['expires_at'] = (datetime.utcnow() + timedelta(hours=24)).isoformat()
            
            notified_entries.append(WaitlistEntry(**entry))
        
        # Update waitlist
        await self.update_event(
            event_id,
            EventUpdate(custom_fields={**event.custom_fields, 'waitlist': waitlist_data}),
            "system"
        )
        
        return notified_entries
    
    async def get_waitlist_stats(self, event_id: str) -> WaitlistStats:
        """Get waitlist statistics"""
        event = await self.get(event_id)
        if not event:
            raise ValueError("Event not found")
        
        waitlist_data = event.custom_fields.get('waitlist', [])
        
        total_waiting = len([e for e in waitlist_data if e['status'] == 'waiting'])
        total_notified = len([e for e in waitlist_data if e['status'] == 'notified'])
        total_converted = len([e for e in waitlist_data if e['status'] == 'converted'])
        
        conversion_rate = (total_converted / total_notified * 100) if total_notified > 0 else 0
        
        # Calculate average wait time for converted entries
        converted_entries = [e for e in waitlist_data if e['status'] == 'converted']
        if converted_entries:
            wait_times = []
            for entry in converted_entries:
                registered_at = datetime.fromisoformat(entry['registered_at'])
                notified_at = datetime.fromisoformat(entry['notified_at'])
                wait_time = (notified_at - registered_at).total_seconds() / 3600  # hours
                wait_times.append(wait_time)
            average_wait_time = sum(wait_times) / len(wait_times)
        else:
            average_wait_time = None
        
        return WaitlistStats(
            total_waiting=total_waiting,
            total_notified=total_notified,
            total_converted=total_converted,
            conversion_rate=conversion_rate,
            average_wait_time=average_wait_time
        )
    
    # Event statistics and analytics
    
    async def get_event_analytics(self, event_id: str) -> Dict[str, Any]:
        """Get comprehensive event analytics"""
        event = await self.get(event_id)
        if not event:
            raise ValueError("Event not found")
        
        capacity_info = await self.get_capacity_info(event_id)
        waitlist_stats = await self.get_waitlist_stats(event_id)
        
        # Calculate event timeline progress
        now = datetime.utcnow()
        timeline_progress = {}
        
        if event.registration_start_at and event.registration_end_at:
            reg_total = (event.registration_end_at - event.registration_start_at).total_seconds()
            if now < event.registration_start_at:
                timeline_progress['registration'] = 0
            elif now > event.registration_end_at:
                timeline_progress['registration'] = 100
            else:
                reg_elapsed = (now - event.registration_start_at).total_seconds()
                timeline_progress['registration'] = min(100, (reg_elapsed / reg_total * 100))
        
        # Event phase calculation
        phase = "upcoming"
        if event.registration_start_at and now >= event.registration_start_at:
            phase = "registration"
        if event.start_at and now >= event.start_at:
            phase = "active"
        if event.end_at and now >= event.end_at:
            phase = "completed"
        
        return {
            "event_id": event_id,
            "phase": phase,
            "timeline_progress": timeline_progress,
            "capacity": capacity_info,
            "waitlist": waitlist_stats.dict(),
            "registration_stats": event.get_registration_stats(),
            "teams_formed": event.teams_count,
            "submissions_received": event.submissions_count,
            "is_registration_open": event.is_registration_open(),
            "is_team_formation_open": event.is_team_formation_open(),
            "is_submission_open": event.is_submission_open(),
            "is_judging_period": event.is_judging_period()
        }
    
    # Helper methods
    
    async def _validate_status_transition(self, event: Event, new_status: EventStatus) -> None:
        """Validate if status transition is allowed"""
        current_status = EventStatus(event.status)
        
        # Define allowed transitions
        allowed_transitions = {
            EventStatus.DRAFT: [EventStatus.PUBLISHED, EventStatus.CANCELLED],
            EventStatus.PUBLISHED: [EventStatus.REGISTRATION_OPEN, EventStatus.CANCELLED],
            EventStatus.REGISTRATION_OPEN: [EventStatus.REGISTRATION_CLOSED, EventStatus.CANCELLED],
            EventStatus.REGISTRATION_CLOSED: [EventStatus.IN_PROGRESS, EventStatus.CANCELLED],
            EventStatus.IN_PROGRESS: [EventStatus.COMPLETED, EventStatus.CANCELLED],
            EventStatus.COMPLETED: [],  # Terminal state
            EventStatus.CANCELLED: []   # Terminal state
        }
        
        if new_status not in allowed_transitions.get(current_status, []):
            raise ValueError(
                f"Invalid status transition from {current_status.value} to {new_status.value}"
            )
    
    async def _validate_event_for_publishing(self, event: Event) -> List[str]:
        """Validate if event is ready for publishing"""
        errors = []
        
        # Check required fields
        if not event.name or not event.slug:
            errors.append("Event name and slug are required")
        
        if not event.start_at or not event.end_at:
            errors.append("Event start and end times are required")
        
        if event.start_at >= event.end_at:
            errors.append("Event end time must be after start time")
        
        # Check venue/virtual setup
        if event.event_type == EventType.IN_PERSON.value:
            if not (event.venue_name and event.venue_address):
                errors.append("Venue information required for in-person events")
        elif event.event_type == EventType.VIRTUAL.value:
            if not event.virtual_platform:
                errors.append("Virtual platform information required for virtual events")
        elif event.event_type == EventType.HYBRID.value:
            if not (event.venue_name and event.virtual_platform):
                errors.append("Both venue and virtual information required for hybrid events")
        
        # Check registration timing
        if event.registration_start_at and event.registration_end_at:
            if event.registration_start_at >= event.registration_end_at:
                errors.append("Registration end time must be after start time")
            if event.registration_end_at > event.start_at:
                errors.append("Registration must end before event starts")
        
        return errors
    
    async def _log_event_action(
        self, 
        event_id: str, 
        action: str, 
        user_id: str, 
        metadata: Dict[str, Any]
    ) -> None:
        """Log event actions for audit trail"""
        # This would typically log to a dedicated audit table
        # For now, we'll add to event custom_fields
        event = await self.get(event_id)
        if event:
            audit_log = event.custom_fields.get('audit_log', [])
            audit_log.append({
                "timestamp": datetime.utcnow().isoformat(),
                "action": action,
                "user_id": user_id,
                "metadata": metadata
            })
            
            # Keep only last 100 audit entries
            if len(audit_log) > 100:
                audit_log = audit_log[-100:]
            
            event.custom_fields = {**event.custom_fields, 'audit_log': audit_log}
            self.db.commit()
