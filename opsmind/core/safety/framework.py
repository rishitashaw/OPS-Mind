"""
OpsMind Guardrails Framework
Comprehensive safety and reliability mechanisms for the multi-agent system
"""

import asyncio
import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Union
import logging
import json
import traceback
from collections import defaultdict, deque
import psutil
import os

from opsmind.config import logger


class GuardrailType(Enum):
    """Types of guardrails available"""
    VALIDATION = "validation"
    RATE_LIMITING = "rate_limiting"
    CIRCUIT_BREAKER = "circuit_breaker"
    RESOURCE_MONITOR = "resource_monitor"
    DATA_SANITIZATION = "data_sanitization"
    UI_CONTENT_ESCAPING = "ui_content_escaping"
    OUTPUT_VERIFICATION = "output_verification"
    TIMEOUT_CONTROL = "timeout_control"
    RETRY_POLICY = "retry_policy"


class GuardrailStatus(Enum):
    """Status of guardrail checks"""
    PASSED = "passed"
    FAILED = "failed"
    BYPASSED = "bypassed"
    ERROR = "error"


@dataclass
class GuardrailConfig:
    """Configuration for guardrail behavior"""
    name: str
    type: GuardrailType
    enabled: bool = True
    strict_mode: bool = False  # If True, failures block execution
    log_level: str = "INFO"
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: float = 30.0
    custom_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GuardrailResult:
    """Result of a guardrail check"""
    guardrail_name: str
    status: GuardrailStatus
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseGuardrail(ABC):
    """Base class for all guardrails"""
    
    def __init__(self, config: GuardrailConfig):
        self.config = config
        self.stats = {
            'total_checks': 0,
            'passed': 0,
            'failed': 0,
            'bypassed': 0,
            'errors': 0,
            'avg_execution_time': 0.0
        }
        self._lock = threading.Lock()
    
    @abstractmethod
    async def check(self, context: Dict[str, Any]) -> GuardrailResult:
        """Perform the guardrail check"""
        pass
    
    def update_stats(self, result: GuardrailResult):
        """Update guardrail statistics"""
        with self._lock:
            self.stats['total_checks'] += 1
            self.stats[result.status.value] += 1
            
            # Update average execution time
            current_avg = self.stats['avg_execution_time']
            total_checks = self.stats['total_checks']
            self.stats['avg_execution_time'] = (
                (current_avg * (total_checks - 1) + result.execution_time) / total_checks
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get guardrail statistics"""
        with self._lock:
            return self.stats.copy()


class ValidationGuardrail(BaseGuardrail):
    """Validates input data structure and content"""
    
    def __init__(self, config: GuardrailConfig):
        super().__init__(config)
        self.required_fields = config.custom_params.get('required_fields', [])
        self.field_types = config.custom_params.get('field_types', {})
        self.max_field_length = config.custom_params.get('max_field_length', 10000)
        self.forbidden_patterns = config.custom_params.get('forbidden_patterns', [])
    
    async def check(self, context: Dict[str, Any]) -> GuardrailResult:
        """Validate input data"""
        start_time = time.time()
        
        try:
            data = context.get('data', {})
            
            # Check required fields
            missing_fields = [field for field in self.required_fields if field not in data]
            if missing_fields:
                return GuardrailResult(
                    guardrail_name=self.config.name,
                    status=GuardrailStatus.FAILED,
                    message=f"Missing required fields: {missing_fields}",
                    execution_time=time.time() - start_time
                )
            
            # Check field types
            for field, expected_type in self.field_types.items():
                if field in data and not isinstance(data[field], expected_type):
                    return GuardrailResult(
                        guardrail_name=self.config.name,
                        status=GuardrailStatus.FAILED,
                        message=f"Field '{field}' has incorrect type. Expected {expected_type.__name__}",
                        execution_time=time.time() - start_time
                    )
            
            # Check field lengths
            for field, value in data.items():
                if isinstance(value, str) and len(value) > self.max_field_length:
                    return GuardrailResult(
                        guardrail_name=self.config.name,
                        status=GuardrailStatus.FAILED,
                        message=f"Field '{field}' exceeds maximum length of {self.max_field_length}",
                        execution_time=time.time() - start_time
                    )
            
            # Check for forbidden patterns
            for field, value in data.items():
                if isinstance(value, str):
                    for pattern in self.forbidden_patterns:
                        if pattern.lower() in value.lower():
                            return GuardrailResult(
                                guardrail_name=self.config.name,
                                status=GuardrailStatus.FAILED,
                                message=f"Field '{field}' contains forbidden pattern: {pattern}",
                                execution_time=time.time() - start_time
                            )
            
            return GuardrailResult(
                guardrail_name=self.config.name,
                status=GuardrailStatus.PASSED,
                message="Validation passed",
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return GuardrailResult(
                guardrail_name=self.config.name,
                status=GuardrailStatus.ERROR,
                message=f"Validation error: {str(e)}",
                execution_time=time.time() - start_time
            )


class RateLimitGuardrail(BaseGuardrail):
    """Rate limiting guardrail to prevent system overload"""
    
    def __init__(self, config: GuardrailConfig):
        super().__init__(config)
        self.max_requests = config.custom_params.get('max_requests', 100)
        self.time_window = config.custom_params.get('time_window', 60)  # seconds
        self.request_times = deque()
        self._lock = threading.Lock()
    
    async def check(self, context: Dict[str, Any]) -> GuardrailResult:
        """Check rate limits"""
        start_time = time.time()
        current_time = time.time()
        
        try:
            with self._lock:
                # Remove old requests outside the time window
                while self.request_times and current_time - self.request_times[0] > self.time_window:
                    self.request_times.popleft()
                
                # Check if we're within rate limits
                if len(self.request_times) >= self.max_requests:
                    return GuardrailResult(
                        guardrail_name=self.config.name,
                        status=GuardrailStatus.FAILED,
                        message=f"Rate limit exceeded: {len(self.request_times)} requests in {self.time_window}s window",
                        execution_time=time.time() - start_time,
                        metadata={'current_requests': len(self.request_times), 'limit': self.max_requests}
                    )
                
                # Record this request
                self.request_times.append(current_time)
            
            return GuardrailResult(
                guardrail_name=self.config.name,
                status=GuardrailStatus.PASSED,
                message="Rate limit check passed",
                execution_time=time.time() - start_time,
                metadata={'current_requests': len(self.request_times), 'limit': self.max_requests}
            )
            
        except Exception as e:
            return GuardrailResult(
                guardrail_name=self.config.name,
                status=GuardrailStatus.ERROR,
                message=f"Rate limit error: {str(e)}",
                execution_time=time.time() - start_time
            )


class CircuitBreakerGuardrail(BaseGuardrail):
    """Circuit breaker pattern to prevent cascading failures"""
    
    def __init__(self, config: GuardrailConfig):
        super().__init__(config)
        self.failure_threshold = config.custom_params.get('failure_threshold', 5)
        self.recovery_timeout = config.custom_params.get('recovery_timeout', 60)
        self.test_requests = config.custom_params.get('test_requests', 1)
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self.success_count = 0
        self._lock = threading.Lock()
    
    async def check(self, context: Dict[str, Any]) -> GuardrailResult:
        """Check circuit breaker state"""
        start_time = time.time()
        
        try:
            with self._lock:
                current_time = time.time()
                
                # Check if we should transition from OPEN to HALF_OPEN
                if (self.state == 'OPEN' and self.last_failure_time and 
                    current_time - self.last_failure_time > self.recovery_timeout):
                    self.state = 'HALF_OPEN'
                    self.success_count = 0
                
                # Handle different states
                if self.state == 'OPEN':
                    return GuardrailResult(
                        guardrail_name=self.config.name,
                        status=GuardrailStatus.FAILED,
                        message=f"Circuit breaker is OPEN. Blocking request.",
                        execution_time=time.time() - start_time,
                        metadata={'state': self.state, 'failure_count': self.failure_count}
                    )
                
                elif self.state == 'HALF_OPEN':
                    if self.success_count >= self.test_requests:
                        return GuardrailResult(
                            guardrail_name=self.config.name,
                            status=GuardrailStatus.FAILED,
                            message=f"Circuit breaker is HALF_OPEN. Limiting requests.",
                            execution_time=time.time() - start_time,
                            metadata={'state': self.state, 'success_count': self.success_count}
                        )
                
                # CLOSED or HALF_OPEN with available test requests
                return GuardrailResult(
                    guardrail_name=self.config.name,
                    status=GuardrailStatus.PASSED,
                    message=f"Circuit breaker allows request. State: {self.state}",
                    execution_time=time.time() - start_time,
                    metadata={'state': self.state, 'failure_count': self.failure_count}
                )
                
        except Exception as e:
            return GuardrailResult(
                guardrail_name=self.config.name,
                status=GuardrailStatus.ERROR,
                message=f"Circuit breaker error: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def record_success(self):
        """Record a successful operation"""
        with self._lock:
            if self.state == 'HALF_OPEN':
                self.success_count += 1
                if self.success_count >= self.test_requests:
                    self.state = 'CLOSED'
                    self.failure_count = 0
            elif self.state == 'CLOSED':
                self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self):
        """Record a failed operation"""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
            elif self.state == 'HALF_OPEN':
                self.state = 'OPEN'


class ResourceMonitorGuardrail(BaseGuardrail):
    """Monitor system resources to prevent overload"""
    
    def __init__(self, config: GuardrailConfig):
        super().__init__(config)
        self.max_cpu_percent = config.custom_params.get('max_cpu_percent', 80)
        self.max_memory_percent = config.custom_params.get('max_memory_percent', 80)
        self.max_disk_percent = config.custom_params.get('max_disk_percent', 90)
        self.max_open_files = config.custom_params.get('max_open_files', 1000)
    
    async def check(self, context: Dict[str, Any]) -> GuardrailResult:
        """Check system resources"""
        start_time = time.time()
        
        try:
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            if cpu_percent > self.max_cpu_percent:
                return GuardrailResult(
                    guardrail_name=self.config.name,
                    status=GuardrailStatus.FAILED,
                    message=f"CPU usage too high: {cpu_percent}% > {self.max_cpu_percent}%",
                    execution_time=time.time() - start_time,
                    metadata={'cpu_percent': cpu_percent, 'limit': self.max_cpu_percent}
                )
            
            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > self.max_memory_percent:
                return GuardrailResult(
                    guardrail_name=self.config.name,
                    status=GuardrailStatus.FAILED,
                    message=f"Memory usage too high: {memory.percent}% > {self.max_memory_percent}%",
                    execution_time=time.time() - start_time,
                    metadata={'memory_percent': memory.percent, 'limit': self.max_memory_percent}
                )
            
            # Check disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            if disk_percent > self.max_disk_percent:
                return GuardrailResult(
                    guardrail_name=self.config.name,
                    status=GuardrailStatus.FAILED,
                    message=f"Disk usage too high: {disk_percent:.1f}% > {self.max_disk_percent}%",
                    execution_time=time.time() - start_time,
                    metadata={'disk_percent': disk_percent, 'limit': self.max_disk_percent}
                )
            
            # Check open files
            process = psutil.Process()
            open_files = len(process.open_files())
            if open_files > self.max_open_files:
                return GuardrailResult(
                    guardrail_name=self.config.name,
                    status=GuardrailStatus.FAILED,
                    message=f"Too many open files: {open_files} > {self.max_open_files}",
                    execution_time=time.time() - start_time,
                    metadata={'open_files': open_files, 'limit': self.max_open_files}
                )
            
            return GuardrailResult(
                guardrail_name=self.config.name,
                status=GuardrailStatus.PASSED,
                message="Resource usage within limits",
                execution_time=time.time() - start_time,
                metadata={
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'disk_percent': disk_percent,
                    'open_files': open_files
                }
            )
            
        except Exception as e:
            return GuardrailResult(
                guardrail_name=self.config.name,
                status=GuardrailStatus.ERROR,
                message=f"Resource monitoring error: {str(e)}",
                execution_time=time.time() - start_time
            )


class DataSanitizationGuardrail(BaseGuardrail):
    """Sanitize input data to prevent injection attacks"""
    
    def __init__(self, config: GuardrailConfig):
        super().__init__(config)
        self.max_string_length = config.custom_params.get('max_string_length', 10000)
        self.forbidden_sql_keywords = config.custom_params.get('forbidden_sql_keywords', [
            'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE', 'EXEC'
        ])
        self.forbidden_script_tags = config.custom_params.get('forbidden_script_tags', [
            '<script', '</script>', '<iframe', '</iframe>', 'javascript:', 'vbscript:'
        ])
    
    async def check(self, context: Dict[str, Any]) -> GuardrailResult:
        """Sanitize input data"""
        start_time = time.time()
        
        try:
            data = context.get('data', {})
            sanitized_data = {}
            issues = []
            
            for key, value in data.items():
                if isinstance(value, str):
                    # Check string length
                    if len(value) > self.max_string_length:
                        issues.append(f"Field '{key}' exceeds maximum length")
                        value = value[:self.max_string_length]
                    
                    # Check for SQL injection patterns
                    value_upper = value.upper()
                    for keyword in self.forbidden_sql_keywords:
                        if keyword in value_upper:
                            issues.append(f"Field '{key}' contains potential SQL injection: {keyword}")
                            value = value.replace(keyword, f"[REMOVED_{keyword}]")
                    
                    # Check for script injection patterns
                    value_lower = value.lower()
                    for tag in self.forbidden_script_tags:
                        if tag.lower() in value_lower:
                            issues.append(f"Field '{key}' contains potential script injection: {tag}")
                            value = value.replace(tag, f"[REMOVED_{tag.upper()}]")
                
                sanitized_data[key] = value
            
            # Update context with sanitized data
            context['data'] = sanitized_data
            
            if issues:
                return GuardrailResult(
                    guardrail_name=self.config.name,
                    status=GuardrailStatus.PASSED,  # Passed but with sanitization
                    message=f"Data sanitized. Issues found: {'; '.join(issues)}",
                    execution_time=time.time() - start_time,
                    metadata={'issues': issues, 'sanitized_fields': len(sanitized_data)}
                )
            else:
                return GuardrailResult(
                    guardrail_name=self.config.name,
                    status=GuardrailStatus.PASSED,
                    message="No sanitization required",
                    execution_time=time.time() - start_time
                )
                
        except Exception as e:
            return GuardrailResult(
                guardrail_name=self.config.name,
                status=GuardrailStatus.ERROR,
                message=f"Data sanitization error: {str(e)}",
                execution_time=time.time() - start_time
            )


class UIContentEscapingGuardrail(BaseGuardrail):
    """
    UI Content Escaping Guardrail - Prevents XSS and data exfiltration
    
    Based on Google ADK safety recommendations for escaping model-generated content in UIs.
    Prevents indirect prompt injection attacks that try to inject malicious HTML/JS content.
    """
    
    def __init__(self, config: GuardrailConfig):
        super().__init__(config)
        
        # HTML entities to escape
        self.html_entities = {
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;',
            '&': '&amp;',
        }
        
        # Dangerous HTML tags that should be completely removed or escaped
        self.dangerous_tags = config.custom_params.get('dangerous_tags', [
            'script', 'iframe', 'object', 'embed', 'applet', 'form', 'input',
            'button', 'textarea', 'select', 'option', 'link', 'meta', 'base',
            'style', 'title', 'head', 'body', 'html', 'frameset', 'frame'
        ])
        
        # Dangerous attributes that can execute JavaScript
        self.dangerous_attributes = config.custom_params.get('dangerous_attributes', [
            'onclick', 'onload', 'onerror', 'onmouseover', 'onmouseout', 'onfocus',
            'onblur', 'onchange', 'onsubmit', 'onreset', 'onselect', 'onkeypress',
            'onkeydown', 'onkeyup', 'onabort', 'onunload', 'onresize', 'onmove',
            'ondblclick', 'oncontextmenu', 'onfocusin', 'onfocusout', 'oninput',
            'oninvalid', 'ondrag', 'ondrop', 'javascript:', 'vbscript:', 'data:'
        ])
        
        # Suspicious URL patterns that could be used for data exfiltration
        self.suspicious_url_patterns = config.custom_params.get('suspicious_url_patterns', [
            'javascript:', 'vbscript:', 'data:', 'file:', 'ftp://', 'about:',
            'chrome:', 'chrome-extension:', 'moz-extension:', 'ms-appx:',
            'x-apple-data-detectors:', 'content:', 'cid:', 'mid:'
        ])
        
        # Image tags with external URLs (potential data exfiltration)
        self.external_img_pattern = r'<img[^>]+src\s*=\s*["\']?https?://(?!localhost)[^"\'>\s]+'
        
        # Enable/disable strict mode for different escaping levels
        self.escape_level = config.custom_params.get('escape_level', 'moderate')  # 'strict', 'moderate', 'basic'
    
    async def check(self, context: Dict[str, Any]) -> GuardrailResult:
        """Escape UI content to prevent XSS and data exfiltration"""
        start_time = time.time()
        
        try:
            # Get content from different possible sources
            content_sources = []
            
            # Check data fields
            data = context.get('data', {})
            for key, value in data.items():
                if isinstance(value, str):
                    content_sources.append((f"data.{key}", value))
            
            # Check direct content field
            if 'content' in context:
                content_sources.append(('content', str(context['content'])))
            
            # Check response/output content
            if 'response' in context:
                content_sources.append(('response', str(context['response'])))
            
            # Check kwargs for any string content
            kwargs = context.get('kwargs', {})
            for key, value in kwargs.items():
                if isinstance(value, str) and len(value) > 10:  # Only check substantial text
                    content_sources.append((f"kwargs.{key}", value))
            
            escaped_content = {}
            security_issues = []
            
            for source_name, content in content_sources:
                if not content:
                    continue
                
                escaped, issues = self._escape_content(content)
                escaped_content[source_name] = escaped
                security_issues.extend([f"{source_name}: {issue}" for issue in issues])
            
            # Update context with escaped content
            for source_name, escaped in escaped_content.items():
                if source_name.startswith('data.'):
                    field_name = source_name[5:]  # Remove 'data.' prefix
                    context['data'][field_name] = escaped
                elif source_name in context:
                    context[source_name] = escaped
                elif source_name.startswith('kwargs.'):
                    field_name = source_name[7:]  # Remove 'kwargs.' prefix
                    context['kwargs'][field_name] = escaped
            
            if security_issues:
                return GuardrailResult(
                    guardrail_name=self.config.name,
                    status=GuardrailStatus.PASSED,  # Passed with fixes
                    message=f"UI content escaped. Security issues found and fixed: {'; '.join(security_issues)}",
                    execution_time=time.time() - start_time,
                    metadata={
                        'security_issues': security_issues,
                        'escaped_sources': list(escaped_content.keys()),
                        'escape_level': self.escape_level
                    }
                )
            else:
                return GuardrailResult(
                    guardrail_name=self.config.name,
                    status=GuardrailStatus.PASSED,
                    message="No UI escaping required",
                    execution_time=time.time() - start_time,
                    metadata={'escape_level': self.escape_level}
                )
                
        except Exception as e:
            return GuardrailResult(
                guardrail_name=self.config.name,
                status=GuardrailStatus.ERROR,
                message=f"UI content escaping error: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def _escape_content(self, content: str) -> tuple[str, list[str]]:
        """Escape content and return (escaped_content, list_of_issues)"""
        import re
        
        original_content = content
        issues = []
        
        # 1. Check for and handle dangerous HTML tags
        for tag in self.dangerous_tags:
            tag_pattern = f'<{tag}[^>]*>.*?</{tag}>|<{tag}[^>]*/?>'
            if re.search(tag_pattern, content, re.IGNORECASE | re.DOTALL):
                issues.append(f"Dangerous HTML tag removed: <{tag}>")
                if self.escape_level == 'strict':
                    # Remove completely
                    content = re.sub(tag_pattern, f'[REMOVED_{tag.upper()}_TAG]', content, flags=re.IGNORECASE | re.DOTALL)
                else:
                    # Escape the tag
                    content = re.sub(f'<({tag})', r'&lt;\1', content, flags=re.IGNORECASE)
                    content = re.sub(f'<(/?)({tag})', r'&lt;\1\2', content, flags=re.IGNORECASE)
        
        # 2. Check for dangerous attributes
        for attr in self.dangerous_attributes:
            if attr.lower() in content.lower():
                issues.append(f"Dangerous attribute found: {attr}")
                # Remove or escape the attribute
                if ':' in attr:  # Protocol like javascript:
                    content = content.replace(attr, f'[REMOVED_{attr.replace(":", "_").upper()}]')
                else:  # Event handler like onclick
                    attr_pattern = f'{attr}\s*=\s*["\'][^"\']*["\']'
                    content = re.sub(attr_pattern, f'[REMOVED_{attr.upper()}]', content, flags=re.IGNORECASE)
        
        # 3. Check for suspicious URL patterns
        for pattern in self.suspicious_url_patterns:
            if pattern.lower() in content.lower():
                issues.append(f"Suspicious URL pattern found: {pattern}")
                content = content.replace(pattern, f'[REMOVED_{pattern.replace(":", "_").upper()}]')
        
        # 4. Check for external image tags (potential data exfiltration)
        if re.search(self.external_img_pattern, content, re.IGNORECASE):
            issues.append("External image tag found (potential data exfiltration)")
            content = re.sub(self.external_img_pattern, '[REMOVED_EXTERNAL_IMG]', content, flags=re.IGNORECASE)
        
        # 5. Basic HTML entity escaping
        if self.escape_level in ['strict', 'moderate']:
            # Always escape basic HTML entities to prevent XSS
            for char, entity in self.html_entities.items():
                if char in content:
                    content = content.replace(char, entity)
                    if char in ['<', '>', '"', "'"] and char in original_content:
                        issues.append(f"HTML entity escaped: {char}")
        
        # 6. Check for potential indirect prompt injection patterns
        injection_patterns = [
            r'<img[^>]+src[^>]*=.*?[\'"][^\'">]*\?.*?[\'"]',  # Image with query params
            r'<img[^>]+src[^>]*=.*?[\'"].*?\.php.*?[\'"]',    # Dynamic image URLs
            r'<a[^>]+href[^>]*=.*?[\'"].*?\?.*?[\'"]',        # Links with query params
            r'fetch\s*\(\s*[\'"].*?[\'"]',                    # Fetch API calls
            r'XMLHttpRequest|xhr\.open',                      # AJAX requests
            r'document\.location|window\.location',           # Location manipulation
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                issues.append("Potential indirect prompt injection pattern detected")
                # Replace with safe placeholder
                content = re.sub(pattern, '[REMOVED_SUSPICIOUS_CODE]', content, flags=re.IGNORECASE)
        
        return content, issues


class GuardrailManager:
    """Manages and orchestrates multiple guardrails"""
    
    def __init__(self):
        self.guardrails: Dict[str, BaseGuardrail] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
        self._lock = threading.Lock()
        
        # Guardrail factories
        self.guardrail_factories = {
            GuardrailType.VALIDATION: ValidationGuardrail,
            GuardrailType.RATE_LIMITING: RateLimitGuardrail,
            GuardrailType.CIRCUIT_BREAKER: CircuitBreakerGuardrail,
            GuardrailType.RESOURCE_MONITOR: ResourceMonitorGuardrail,
            GuardrailType.DATA_SANITIZATION: DataSanitizationGuardrail,
            GuardrailType.UI_CONTENT_ESCAPING: UIContentEscapingGuardrail,
        }
    
    def add_guardrail(self, config: GuardrailConfig) -> bool:
        """Add a new guardrail"""
        try:
            if config.type not in self.guardrail_factories:
                logger.error(f"Unknown guardrail type: {config.type}")
                return False
            
            guardrail_class = self.guardrail_factories[config.type]
            guardrail = guardrail_class(config)
            
            with self._lock:
                self.guardrails[config.name] = guardrail
            
            logger.info(f"Added guardrail: {config.name} ({config.type.value})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add guardrail {config.name}: {e}")
            return False
    
    def remove_guardrail(self, name: str) -> bool:
        """Remove a guardrail"""
        try:
            with self._lock:
                if name in self.guardrails:
                    del self.guardrails[name]
                    logger.info(f"Removed guardrail: {name}")
                    return True
                else:
                    logger.warning(f"Guardrail not found: {name}")
                    return False
        except Exception as e:
            logger.error(f"Failed to remove guardrail {name}: {e}")
            return False
    
    async def check_all(self, context: Dict[str, Any], agent_name: str = "unknown") -> Dict[str, Any]:
        """Run all enabled guardrails"""
        start_time = time.time()
        results = []
        passed = 0
        failed = 0
        errors = 0
        
        try:
            guardrails_to_check = []
            with self._lock:
                guardrails_to_check = [(name, guardrail) for name, guardrail in self.guardrails.items() 
                                     if guardrail.config.enabled]
            
            # Run guardrails
            for name, guardrail in guardrails_to_check:
                try:
                    result = await guardrail.check(context)
                    results.append(result)
                    guardrail.update_stats(result)
                    
                    if result.status == GuardrailStatus.PASSED:
                        passed += 1
                    elif result.status == GuardrailStatus.FAILED:
                        failed += 1
                        # Handle circuit breaker state updates
                        if isinstance(guardrail, CircuitBreakerGuardrail):
                            guardrail.record_failure()
                    elif result.status == GuardrailStatus.ERROR:
                        errors += 1
                        
                except Exception as e:
                    error_result = GuardrailResult(
                        guardrail_name=name,
                        status=GuardrailStatus.ERROR,
                        message=f"Guardrail execution error: {str(e)}"
                    )
                    results.append(error_result)
                    errors += 1
            
            # Record execution history
            execution_record = {
                'timestamp': datetime.now().isoformat(),
                'agent_name': agent_name,
                'total_guardrails': len(guardrails_to_check),
                'passed': passed,
                'failed': failed,
                'errors': errors,
                'execution_time': time.time() - start_time,
                'results': [result.__dict__ for result in results]
            }
            
            with self._lock:
                self.execution_history.append(execution_record)
                if len(self.execution_history) > self.max_history_size:
                    self.execution_history = self.execution_history[-self.max_history_size:]
            
            # Determine overall status
            has_strict_failures = any(
                result.status == GuardrailStatus.FAILED and 
                self.guardrails[result.guardrail_name].config.strict_mode
                for result in results
            )
            
            overall_status = "blocked" if has_strict_failures else "allowed"
            
            return {
                'status': overall_status,
                'total_guardrails': len(guardrails_to_check),
                'passed': passed,
                'failed': failed,
                'errors': errors,
                'execution_time': time.time() - start_time,
                'results': results,
                'strict_failures': has_strict_failures
            }
            
        except Exception as e:
            logger.error(f"Error in guardrail check_all: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'execution_time': time.time() - start_time
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive guardrail statistics"""
        with self._lock:
            stats = {
                'total_guardrails': len(self.guardrails),
                'enabled_guardrails': len([g for g in self.guardrails.values() if g.config.enabled]),
                'guardrail_stats': {name: guardrail.get_stats() 
                                  for name, guardrail in self.guardrails.items()},
                'recent_executions': len(self.execution_history),
                'execution_history': self.execution_history[-10:]  # Last 10 executions
            }
        
        return stats
    
    def get_health_report(self) -> Dict[str, Any]:
        """Generate a health report for all guardrails"""
        stats = self.get_stats()
        
        health_score = 0
        issues = []
        
        for name, guardrail_stats in stats['guardrail_stats'].items():
            total_checks = guardrail_stats['total_checks']
            if total_checks > 0:
                success_rate = (guardrail_stats['passed'] + guardrail_stats['bypassed']) / total_checks
                health_score += success_rate
                
                if success_rate < 0.9:
                    issues.append(f"Guardrail '{name}' has low success rate: {success_rate:.2%}")
                
                if guardrail_stats['avg_execution_time'] > 5.0:
                    issues.append(f"Guardrail '{name}' has high execution time: {guardrail_stats['avg_execution_time']:.2f}s")
        
        if stats['total_guardrails'] > 0:
            health_score = health_score / stats['total_guardrails']
        
        return {
            'health_score': health_score,
            'status': 'healthy' if health_score > 0.8 and not issues else 'degraded',
            'issues': issues,
            'total_guardrails': stats['total_guardrails'],
            'enabled_guardrails': stats['enabled_guardrails']
        }


# Global guardrail manager instance
_guardrail_manager = None


def get_guardrail_manager() -> GuardrailManager:
    """Get the global guardrail manager instance"""
    global _guardrail_manager
    if _guardrail_manager is None:
        _guardrail_manager = GuardrailManager()
    return _guardrail_manager


def initialize_default_guardrails():
    """Initialize default guardrails for OpsMind"""
    manager = get_guardrail_manager()
    
    # Data validation guardrail
    validation_config = GuardrailConfig(
        name="data_validation",
        type=GuardrailType.VALIDATION,
        enabled=True,
        strict_mode=True,
        custom_params={
            'max_field_length': 50000,
            'forbidden_patterns': ['<script>', 'javascript:', 'vbscript:', 'onload=', 'onerror=']
        }
    )
    manager.add_guardrail(validation_config)
    
    # Rate limiting guardrail
    rate_limit_config = GuardrailConfig(
        name="rate_limiter",
        type=GuardrailType.RATE_LIMITING,
        enabled=True,
        strict_mode=True,
        custom_params={
            'max_requests': 100,
            'time_window': 60
        }
    )
    manager.add_guardrail(rate_limit_config)
    
    # Circuit breaker guardrail
    circuit_breaker_config = GuardrailConfig(
        name="circuit_breaker",
        type=GuardrailType.CIRCUIT_BREAKER,
        enabled=True,
        strict_mode=False,
        custom_params={
            'failure_threshold': 5,
            'recovery_timeout': 60,
            'test_requests': 3
        }
    )
    manager.add_guardrail(circuit_breaker_config)
    
    # Resource monitor guardrail
    resource_monitor_config = GuardrailConfig(
        name="resource_monitor",
        type=GuardrailType.RESOURCE_MONITOR,
        enabled=True,
        strict_mode=False,
        custom_params={
            'max_cpu_percent': 85,
            'max_memory_percent': 85,
            'max_disk_percent': 90,
            'max_open_files': 1000
        }
    )
    manager.add_guardrail(resource_monitor_config)
    
    # Data sanitization guardrail
    sanitization_config = GuardrailConfig(
        name="data_sanitizer",
        type=GuardrailType.DATA_SANITIZATION,
        enabled=True,
        strict_mode=False,
        custom_params={
            'max_string_length': 100000,
            'forbidden_sql_keywords': ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE', 'EXEC'],
            'forbidden_script_tags': ['<script', '</script>', '<iframe', '</iframe>', 'javascript:', 'vbscript:']
        }
    )
    manager.add_guardrail(sanitization_config)
    
    # UI content escaping guardrail (based on Google ADK safety recommendations)
    ui_escaping_config = GuardrailConfig(
        name="ui_content_escaper",
        type=GuardrailType.UI_CONTENT_ESCAPING,
        enabled=True,
        strict_mode=True,  # Critical for preventing XSS and data exfiltration
        custom_params={
            'escape_level': 'moderate',  # 'strict', 'moderate', 'basic'
            'dangerous_tags': [
                'script', 'iframe', 'object', 'embed', 'applet', 'form', 'input',
                'button', 'textarea', 'select', 'option', 'link', 'meta', 'base',
                'style', 'title', 'head', 'body', 'html', 'frameset', 'frame'
            ],
            'dangerous_attributes': [
                'onclick', 'onload', 'onerror', 'onmouseover', 'onmouseout', 'onfocus',
                'onblur', 'onchange', 'onsubmit', 'onreset', 'onselect', 'onkeypress',
                'onkeydown', 'onkeyup', 'onabort', 'onunload', 'onresize', 'onmove',
                'ondblclick', 'oncontextmenu', 'onfocusin', 'onfocusout', 'oninput',
                'oninvalid', 'ondrag', 'ondrop', 'javascript:', 'vbscript:', 'data:'
            ],
            'suspicious_url_patterns': [
                'javascript:', 'vbscript:', 'data:', 'file:', 'ftp://', 'about:',
                'chrome:', 'chrome-extension:', 'moz-extension:', 'ms-appx:'
            ]
        }
    )
    manager.add_guardrail(ui_escaping_config)
    
    logger.info("Initialized default guardrails for OpsMind (including Google ADK UI content escaping)")


# Decorator for automatic guardrail checking
def with_guardrails(agent_name: str = "unknown"):
    """Decorator to automatically apply guardrails to agent functions"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            manager = get_guardrail_manager()
            
            # Prepare context for guardrail checking
            context = {
                'function_name': func.__name__,
                'agent_name': agent_name,
                'args': args,
                'kwargs': kwargs,
                'data': kwargs.get('data', {})
            }
            
            # Run guardrails
            guardrail_result = await manager.check_all(context, agent_name)
            
            # Log guardrail results
            if guardrail_result['status'] == 'blocked':
                logger.warning(f"Guardrails blocked execution for {agent_name}.{func.__name__}")
                raise RuntimeError(f"Guardrails blocked execution: {guardrail_result}")
            elif guardrail_result['failed'] > 0:
                logger.warning(f"Guardrails found {guardrail_result['failed']} issues for {agent_name}.{func.__name__}")
            
            # Execute the original function
            try:
                result = await func(*args, **kwargs)
                
                # Record success for circuit breakers
                for guardrail in manager.guardrails.values():
                    if isinstance(guardrail, CircuitBreakerGuardrail):
                        guardrail.record_success()
                
                return result
                
            except Exception as e:
                # Record failure for circuit breakers
                for guardrail in manager.guardrails.values():
                    if isinstance(guardrail, CircuitBreakerGuardrail):
                        guardrail.record_failure()
                raise
        
        return wrapper
    return decorator