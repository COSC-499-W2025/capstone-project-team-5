"""Pydantic schemas for user and user profile API responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserInfoResponse(BaseModel):
    """Response schema for basic user information."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    created_at: datetime


class UserProfileResponse(BaseModel):
    """Response schema for user profile data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    linkedin_url: str | None = None
    github_username: str | None = None
    website: str | None = None
    updated_at: datetime


class UserProfileCreateRequest(BaseModel):
    """Request schema for creating a user profile."""

    first_name: str | None = Field(None, description="User's first name")
    last_name: str | None = Field(None, description="User's last name")
    email: str | None = Field(None, description="Contact email address")
    phone: str | None = Field(None, description="Phone number")
    address: str | None = Field(None, description="Street address")
    city: str | None = Field(None, description="City name")
    state: str | None = Field(None, description="State/province")
    zip_code: str | None = Field(None, description="Postal/ZIP code")
    linkedin_url: str | None = Field(None, description="LinkedIn profile URL")
    github_username: str | None = Field(None, description="GitHub username")
    website: str | None = Field(None, description="Personal website URL")


class UserProfileUpdateRequest(BaseModel):
    """Request schema for updating a user profile."""

    first_name: str | None = Field(None, description="User's first name")
    last_name: str | None = Field(None, description="User's last name")
    email: str | None = Field(None, description="Contact email address")
    phone: str | None = Field(None, description="Phone number")
    address: str | None = Field(None, description="Street address")
    city: str | None = Field(None, description="City name")
    state: str | None = Field(None, description="State/province")
    zip_code: str | None = Field(None, description="Postal/ZIP code")
    linkedin_url: str | None = Field(None, description="LinkedIn profile URL")
    github_username: str | None = Field(None, description="GitHub username")
    website: str | None = Field(None, description="Personal website URL")
