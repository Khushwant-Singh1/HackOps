"""
Events API endpoints for comprehensive event management
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.event_service import EventService
from app.schemas.event import (
    EventCreate, EventUpdate, EventStatusUpdate, EventResponse, EventListResponse,
    EventWizardStep1, EventWizardStep2, EventWizardStep3, EventWizardStep4, 
    EventWizardStep5, EventWizardStep6, ScheduleItem, Room, ConflictDetection,
    WaitlistEntry, WaitlistStats
)
from app.models.event import EventStatus, EventType, EventVisibility

router = APIRouter()


# Dependency to get event service
async def get_event_service(
    db: Session = Depends(get_db),
    tenant_id: str = Query("default-tenant", description="Tenant ID")
) -> EventService:
    """Get event service instance with tenant context"""
    return EventService(db, tenant_id)


# Core CRUD endpoints

@router.get("/", response_model=EventListResponse)
async def list_events(
    skip: int = Query(0, ge=0, description="Number of events to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of events to return"),
    status: Optional[EventStatus] = Query(None, description="Filter by event status"),
    event_type: Optional[EventType] = Query(None, description="Filter by event type"),
    visibility: Optional[EventVisibility] = Query(None, description="Filter by visibility"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    upcoming_only: bool = Query(False, description="Show only upcoming events"),
    published_only: bool = Query(False, description="Show only published events"),
    event_service: EventService = Depends(get_event_service)
):
    """Get paginated list of events with filtering"""
    try:
        events, total = await event_service.get_events_list(
            skip=skip,
            limit=limit,
            status=status,
            event_type=event_type,
            visibility=visibility,
            search=search,
            upcoming_only=upcoming_only,
            published_only=published_only
        )
        
        # Convert to response format
        event_responses = []
        for event in events:
            event_response = EventResponse.from_orm(event)
            # Add computed properties
            event_response.is_published = event.is_published()
            event_response.is_registration_open = event.is_registration_open()
            event_response.is_team_formation_open = event.is_team_formation_open()
            event_response.is_submission_open = event.is_submission_open()
            event_response.is_judging_period = event.is_judging_period()
            event_response.capacity_remaining = event.capacity_remaining()
            event_response.is_at_capacity = event.is_at_capacity()
            event_responses.append(event_response)
        
        total_pages = (total + limit - 1) // limit
        
        return EventListResponse(
            events=event_responses,
            total=total,
            page=(skip // limit) + 1,
            per_page=limit,
            total_pages=total_pages
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve events: {str(e)}"
        )


@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_data: EventCreate,
    creator_id: str = Query(..., description="ID of the user creating the event"),
    event_service: EventService = Depends(get_event_service)
):
    """Create a new event"""
    try:
        event = await event_service.create_event(event_data, creator_id)
        
        # Convert to response format
        event_response = EventResponse.from_orm(event)
        event_response.is_published = event.is_published()
        event_response.is_registration_open = event.is_registration_open()
        event_response.is_team_formation_open = event.is_team_formation_open()
        event_response.is_submission_open = event.is_submission_open()
        event_response.is_judging_period = event.is_judging_period()
        event_response.capacity_remaining = event.capacity_remaining()
        event_response.is_at_capacity = event.is_at_capacity()
        
        return event_response
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create event: {str(e)}"
        )


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: str = Path(..., description="Event ID"),
    event_service: EventService = Depends(get_event_service)
):
    """Get event by ID"""
    try:
        event = await event_service.get(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        # Convert to response format
        event_response = EventResponse.from_orm(event)
        event_response.is_published = event.is_published()
        event_response.is_registration_open = event.is_registration_open()
        event_response.is_team_formation_open = event.is_team_formation_open()
        event_response.is_submission_open = event.is_submission_open()
        event_response.is_judging_period = event.is_judging_period()
        event_response.capacity_remaining = event.capacity_remaining()
        event_response.is_at_capacity = event.is_at_capacity()
        
        return event_response
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve event: {str(e)}"
        )


@router.get("/slug/{slug}", response_model=EventResponse)
async def get_event_by_slug(
    slug: str = Path(..., description="Event slug"),
    event_service: EventService = Depends(get_event_service)
):
    """Get event by slug"""
    try:
        event = await event_service.get_by_slug(slug)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        # Convert to response format
        event_response = EventResponse.from_orm(event)
        event_response.is_published = event.is_published()
        event_response.is_registration_open = event.is_registration_open()
        event_response.is_team_formation_open = event.is_team_formation_open()
        event_response.is_submission_open = event.is_submission_open()
        event_response.is_judging_period = event.is_judging_period()
        event_response.capacity_remaining = event.capacity_remaining()
        event_response.is_at_capacity = event.is_at_capacity()
        
        return event_response
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve event: {str(e)}"
        )


@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: str = Path(..., description="Event ID"),
    update_data: EventUpdate = ...,
    updater_id: str = Query(..., description="ID of the user updating the event"),
    event_service: EventService = Depends(get_event_service)
):
    """Update an event"""
    try:
        event = await event_service.update_event(event_id, update_data, updater_id)
        
        # Convert to response format
        event_response = EventResponse.from_orm(event)
        event_response.is_published = event.is_published()
        event_response.is_registration_open = event.is_registration_open()
        event_response.is_team_formation_open = event.is_team_formation_open()
        event_response.is_submission_open = event.is_submission_open()
        event_response.is_judging_period = event.is_judging_period()
        event_response.capacity_remaining = event.capacity_remaining()
        event_response.is_at_capacity = event.is_at_capacity()
        
        return event_response
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update event: {str(e)}"
        )


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: str = Path(..., description="Event ID"),
    deleter_id: str = Query(..., description="ID of the user deleting the event"),
    event_service: EventService = Depends(get_event_service)
):
    """Soft delete an event"""
    try:
        success = await event_service.delete(event_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete event: {str(e)}"
        )


# Event lifecycle management endpoints

@router.patch("/{event_id}/status", response_model=EventResponse)
async def update_event_status(
    event_id: str = Path(..., description="Event ID"),
    status_update: EventStatusUpdate = ...,
    updater_id: str = Query(..., description="ID of the user updating the status"),
    event_service: EventService = Depends(get_event_service)
):
    """Update event status with validation"""
    try:
        event = await event_service.update_event_status(event_id, status_update, updater_id)
        
        # Convert to response format
        event_response = EventResponse.from_orm(event)
        event_response.is_published = event.is_published()
        event_response.is_registration_open = event.is_registration_open()
        event_response.is_team_formation_open = event.is_team_formation_open()
        event_response.is_submission_open = event.is_submission_open()
        event_response.is_judging_period = event.is_judging_period()
        event_response.capacity_remaining = event.capacity_remaining()
        event_response.is_at_capacity = event.is_at_capacity()
        
        return event_response
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update event status: {str(e)}"
        )


@router.post("/{event_id}/publish", response_model=EventResponse)
async def publish_event(
    event_id: str = Path(..., description="Event ID"),
    publisher_id: str = Query(..., description="ID of the user publishing the event"),
    event_service: EventService = Depends(get_event_service)
):
    """Publish an event (move from DRAFT to PUBLISHED)"""
    try:
        event = await event_service.publish_event(event_id, publisher_id)
        
        # Convert to response format
        event_response = EventResponse.from_orm(event)
        event_response.is_published = event.is_published()
        event_response.is_registration_open = event.is_registration_open()
        event_response.is_team_formation_open = event.is_team_formation_open()
        event_response.is_submission_open = event.is_submission_open()
        event_response.is_judging_period = event.is_judging_period()
        event_response.capacity_remaining = event.capacity_remaining()
        event_response.is_at_capacity = event.is_at_capacity()
        
        return event_response
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to publish event: {str(e)}"
        )


@router.post("/{event_id}/registration/open", response_model=EventResponse)
async def open_registration(
    event_id: str = Path(..., description="Event ID"),
    opener_id: str = Query(..., description="ID of the user opening registration"),
    event_service: EventService = Depends(get_event_service)
):
    """Open event registration"""
    try:
        event = await event_service.open_registration(event_id, opener_id)
        
        # Convert to response format
        event_response = EventResponse.from_orm(event)
        event_response.is_published = event.is_published()
        event_response.is_registration_open = event.is_registration_open()
        event_response.is_team_formation_open = event.is_team_formation_open()
        event_response.is_submission_open = event.is_submission_open()
        event_response.is_judging_period = event.is_judging_period()
        event_response.capacity_remaining = event.capacity_remaining()
        event_response.is_at_capacity = event.is_at_capacity()
        
        return event_response
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to open registration: {str(e)}"
        )


@router.post("/{event_id}/registration/close", response_model=EventResponse)
async def close_registration(
    event_id: str = Path(..., description="Event ID"),
    closer_id: str = Query(..., description="ID of the user closing registration"),
    event_service: EventService = Depends(get_event_service)
):
    """Close event registration"""
    try:
        event = await event_service.close_registration(event_id, closer_id)
        
        # Convert to response format
        event_response = EventResponse.from_orm(event)
        event_response.is_published = event.is_published()
        event_response.is_registration_open = event.is_registration_open()
        event_response.is_team_formation_open = event.is_team_formation_open()
        event_response.is_submission_open = event.is_submission_open()
        event_response.is_judging_period = event.is_judging_period()
        event_response.capacity_remaining = event.capacity_remaining()
        event_response.is_at_capacity = event.is_at_capacity()
        
        return event_response
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to close registration: {str(e)}"
        )


@router.post("/{event_id}/start", response_model=EventResponse)
async def start_event(
    event_id: str = Path(..., description="Event ID"),
    starter_id: str = Query(..., description="ID of the user starting the event"),
    event_service: EventService = Depends(get_event_service)
):
    """Start event (move to IN_PROGRESS)"""
    try:
        event = await event_service.start_event(event_id, starter_id)
        
        # Convert to response format
        event_response = EventResponse.from_orm(event)
        event_response.is_published = event.is_published()
        event_response.is_registration_open = event.is_registration_open()
        event_response.is_team_formation_open = event.is_team_formation_open()
        event_response.is_submission_open = event.is_submission_open()
        event_response.is_judging_period = event.is_judging_period()
        event_response.capacity_remaining = event.capacity_remaining()
        event_response.is_at_capacity = event.is_at_capacity()
        
        return event_response
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start event: {str(e)}"
        )


@router.post("/{event_id}/complete", response_model=EventResponse)
async def complete_event(
    event_id: str = Path(..., description="Event ID"),
    completer_id: str = Query(..., description="ID of the user completing the event"),
    event_service: EventService = Depends(get_event_service)
):
    """Complete event"""
    try:
        event = await event_service.complete_event(event_id, completer_id)
        
        # Convert to response format
        event_response = EventResponse.from_orm(event)
        event_response.is_published = event.is_published()
        event_response.is_registration_open = event.is_registration_open()
        event_response.is_team_formation_open = event.is_team_formation_open()
        event_response.is_submission_open = event.is_submission_open()
        event_response.is_judging_period = event.is_judging_period()
        event_response.capacity_remaining = event.capacity_remaining()
        event_response.is_at_capacity = event.is_at_capacity()
        
        return event_response
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete event: {str(e)}"
        )


@router.post("/{event_id}/cancel", response_model=EventResponse)
async def cancel_event(
    event_id: str = Path(..., description="Event ID"),
    reason: str = Query(..., description="Reason for cancellation"),
    canceller_id: str = Query(..., description="ID of the user cancelling the event"),
    event_service: EventService = Depends(get_event_service)
):
    """Cancel event"""
    try:
        event = await event_service.cancel_event(event_id, canceller_id, reason)
        
        # Convert to response format
        event_response = EventResponse.from_orm(event)
        event_response.is_published = event.is_published()
        event_response.is_registration_open = event.is_registration_open()
        event_response.is_team_formation_open = event.is_team_formation_open()
        event_response.is_submission_open = event.is_submission_open()
        event_response.is_judging_period = event.is_judging_period()
        event_response.capacity_remaining = event.capacity_remaining()
        event_response.is_at_capacity = event.is_at_capacity()
        
        return event_response
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel event: {str(e)}"
        )


# Event wizard endpoints

@router.post("/wizard/step1")
async def create_event_wizard_step1(
    step_data: EventWizardStep1,
    creator_id: str = Query(..., description="ID of the user creating the event"),
    event_service: EventService = Depends(get_event_service)
):
    """Process event creation wizard step 1: Basic information"""
    try:
        result = await event_service.create_event_wizard_step1(step_data, creator_id)
        return result
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process wizard step 1: {str(e)}"
        )


@router.put("/wizard/{event_id}/step2")
async def update_event_wizard_step2(
    event_id: str = Path(..., description="Event ID"),
    step_data: EventWizardStep2 = ...,
    updater_id: str = Query(..., description="ID of the user updating the event"),
    event_service: EventService = Depends(get_event_service)
):
    """Process event creation wizard step 2: Timing"""
    try:
        result = await event_service.update_event_wizard_step2(event_id, step_data, updater_id)
        return result
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process wizard step 2: {str(e)}"
        )


@router.put("/wizard/{event_id}/step3")
async def update_event_wizard_step3(
    event_id: str = Path(..., description="Event ID"),
    step_data: EventWizardStep3 = ...,
    updater_id: str = Query(..., description="ID of the user updating the event"),
    event_service: EventService = Depends(get_event_service)
):
    """Process event creation wizard step 3: Venue/Virtual setup"""
    try:
        result = await event_service.update_event_wizard_step3(event_id, step_data, updater_id)
        return result
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process wizard step 3: {str(e)}"
        )


@router.put("/wizard/{event_id}/step4")
async def update_event_wizard_step4(
    event_id: str = Path(..., description="Event ID"),
    step_data: EventWizardStep4 = ...,
    updater_id: str = Query(..., description="ID of the user updating the event"),
    event_service: EventService = Depends(get_event_service)
):
    """Process event creation wizard step 4: Capacity and teams"""
    try:
        result = await event_service.update_event_wizard_step4(event_id, step_data, updater_id)
        return result
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process wizard step 4: {str(e)}"
        )


@router.put("/wizard/{event_id}/step5")
async def update_event_wizard_step5(
    event_id: str = Path(..., description="Event ID"),
    step_data: EventWizardStep5 = ...,
    updater_id: str = Query(..., description="ID of the user updating the event"),
    event_service: EventService = Depends(get_event_service)
):
    """Process event creation wizard step 5: Registration and submission"""
    try:
        result = await event_service.update_event_wizard_step5(event_id, step_data, updater_id)
        return result
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process wizard step 5: {str(e)}"
        )


@router.put("/wizard/{event_id}/step6")
async def update_event_wizard_step6(
    event_id: str = Path(..., description="Event ID"),
    step_data: EventWizardStep6 = ...,
    updater_id: str = Query(..., description="ID of the user updating the event"),
    event_service: EventService = Depends(get_event_service)
):
    """Process event creation wizard step 6: Final settings"""
    try:
        result = await event_service.update_event_wizard_step6(event_id, step_data, updater_id)
        return result
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process wizard step 6: {str(e)}"
        )


# Schedule management endpoints

@router.get("/{event_id}/schedule", response_model=List[ScheduleItem])
async def get_event_schedule(
    event_id: str = Path(..., description="Event ID"),
    event_service: EventService = Depends(get_event_service)
):
    """Get event schedule items"""
    try:
        schedule = await event_service.get_event_schedule(event_id)
        return schedule
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve schedule: {str(e)}"
        )


@router.post("/{event_id}/schedule", response_model=ScheduleItem, status_code=status.HTTP_201_CREATED)
async def add_schedule_item(
    event_id: str = Path(..., description="Event ID"),
    schedule_item: ScheduleItem = ...,
    creator_id: str = Query(..., description="ID of the user creating the schedule item"),
    event_service: EventService = Depends(get_event_service)
):
    """Add schedule item with conflict detection"""
    try:
        item = await event_service.add_schedule_item(event_id, schedule_item, creator_id)
        return item
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add schedule item: {str(e)}"
        )


@router.post("/{event_id}/schedule/conflicts", response_model=ConflictDetection)
async def detect_schedule_conflicts(
    event_id: str = Path(..., description="Event ID"),
    schedule_item: ScheduleItem = ...,
    event_service: EventService = Depends(get_event_service)
):
    """Detect schedule conflicts for a new item"""
    try:
        conflicts = await event_service.detect_schedule_conflicts(event_id, schedule_item)
        return conflicts
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect conflicts: {str(e)}"
        )


# Room and resource management endpoints

@router.get("/{event_id}/rooms", response_model=List[Room])
async def get_event_rooms(
    event_id: str = Path(..., description="Event ID"),
    event_service: EventService = Depends(get_event_service)
):
    """Get event rooms/spaces"""
    try:
        rooms = await event_service.get_event_rooms(event_id)
        return rooms
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve rooms: {str(e)}"
        )


@router.post("/{event_id}/rooms", response_model=Room, status_code=status.HTTP_201_CREATED)
async def add_room(
    event_id: str = Path(..., description="Event ID"),
    room: Room = ...,
    creator_id: str = Query(..., description="ID of the user adding the room"),
    event_service: EventService = Depends(get_event_service)
):
    """Add room to event"""
    try:
        added_room = await event_service.add_room(event_id, room, creator_id)
        return added_room
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add room: {str(e)}"
        )


@router.get("/{event_id}/rooms/{room_id}/availability")
async def check_room_availability(
    event_id: str = Path(..., description="Event ID"),
    room_id: str = Path(..., description="Room ID"),
    start_at: str = Query(..., description="Start time (ISO format)"),
    end_at: str = Query(..., description="End time (ISO format)"),
    event_service: EventService = Depends(get_event_service)
):
    """Check if room is available for given time period"""
    try:
        from datetime import datetime
        start_datetime = datetime.fromisoformat(start_at.replace('Z', '+00:00'))
        end_datetime = datetime.fromisoformat(end_at.replace('Z', '+00:00'))
        
        is_available = await event_service.check_room_availability(
            event_id, room_id, start_datetime, end_datetime
        )
        
        return {
            "room_id": room_id,
            "start_at": start_at,
            "end_at": end_at,
            "is_available": is_available
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check room availability: {str(e)}"
        )


# Capacity and waitlist endpoints

@router.get("/{event_id}/capacity")
async def get_capacity_info(
    event_id: str = Path(..., description="Event ID"),
    event_service: EventService = Depends(get_event_service)
):
    """Get detailed capacity information"""
    try:
        capacity_info = await event_service.get_capacity_info(event_id)
        return capacity_info
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve capacity info: {str(e)}"
        )


@router.post("/{event_id}/waitlist", response_model=WaitlistEntry, status_code=status.HTTP_201_CREATED)
async def add_to_waitlist(
    event_id: str = Path(..., description="Event ID"),
    user_id: str = Query(..., description="User ID to add to waitlist"),
    event_service: EventService = Depends(get_event_service)
):
    """Add user to event waitlist"""
    try:
        entry = await event_service.add_to_waitlist(event_id, user_id)
        return entry
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add to waitlist: {str(e)}"
        )


@router.post("/{event_id}/waitlist/process", response_model=List[WaitlistEntry])
async def process_waitlist(
    event_id: str = Path(..., description="Event ID"),
    spots_available: int = Query(1, ge=1, description="Number of spots available"),
    event_service: EventService = Depends(get_event_service)
):
    """Process waitlist when spots become available"""
    try:
        notified_entries = await event_service.process_waitlist(event_id, spots_available)
        return notified_entries
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process waitlist: {str(e)}"
        )


@router.get("/{event_id}/waitlist/stats", response_model=WaitlistStats)
async def get_waitlist_stats(
    event_id: str = Path(..., description="Event ID"),
    event_service: EventService = Depends(get_event_service)
):
    """Get waitlist statistics"""
    try:
        stats = await event_service.get_waitlist_stats(event_id)
        return stats
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve waitlist stats: {str(e)}"
        )


# Analytics endpoints

@router.get("/{event_id}/analytics")
async def get_event_analytics(
    event_id: str = Path(..., description="Event ID"),
    event_service: EventService = Depends(get_event_service)
):
    """Get comprehensive event analytics"""
    try:
        analytics = await event_service.get_event_analytics(event_id)
        return analytics
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve analytics: {str(e)}"
        )