# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


import frappe

from erpnext_gocardless_bank.version import is_version_gt


# [Bank, Bank Transaction, Clean, Currency, Internal]
def is_job_running(name: str):
    if is_version_gt(14):
        from frappe.utils.background_jobs import is_job_enqueued
        
        return is_job_enqueued(name)
    
    else:
        from frappe.core.page.background_jobs.background_jobs import get_info
        
        jobs = [d.get("job_name") for d in get_info("Jobs", job_status="active")]
        return True if name in jobs else False


# [Bank, Bank Transaction, Clean, Currency]
def enqueue_job(method: str, job_name: str, **kwargs):
    if "timeout" in kwargs and "queue" not in kwargs:
        from frappe.utils import cint
        
        if cint(kwargs["timeout"]) >= 1500:
            kwargs["queue"] = "long"
        else:
            kwargs["queue"] = "short"
    
    if is_version_gt(14):
        frappe.enqueue(
            method,
            job_id=job_name,
            is_async=True,
            **kwargs
        )
    
    else:
        frappe.enqueue(
            method,
            job_name=job_name,
            is_async=True,
            **kwargs
        )


# [Bank]
def dequeue_job(job_name: str):
    if not is_job_running(job_name):
        return 0
    
    if is_version_gt(14):
        from frappe.utils.background_jobs import get_job
        
        try:
            job = get_job(job_name)
            if job:
                job.cancel()
                job.delete()
        except Exception:
            pass
    
    else:
        from frappe.utils.background_jobs import get_queues
        
        try:
            for queue in get_queues():
                for job in queue.jobs:
                    name = (
                        job.kwargs.get("kwargs", {}).get("playbook_method")
                        or job.kwargs.get("kwargs", {}).get("job_type")
                        or str(job.kwargs.get("job_name"))
                    )
                    if name == job_name:
                        job.cancel()
                        job.delete()
                        return 0
                    
        except Exception:
            pass