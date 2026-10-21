import { useEffect, useId, useRef, useState } from 'react';
import { BookOpen, ChevronDown } from 'lucide-react';

export default function StyledSelect({ label, value, options, onChange, disabled = false, compact = false }) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [openUp, setOpenUp] = useState(false);
  const root = useRef(null);
  const trigger = useRef(null);
  const menu = useRef(null);
  const listId = useId();
  const selectedIndex = Math.max(0, options.findIndex(option => option.value === value));
  const selected = options[selectedIndex];

  useEffect(() => {
    if (!open) return;
    function closeOnOutside(event) {
      if (!root.current?.contains(event.target)) setOpen(false);
    }
    document.addEventListener('pointerdown', closeOnOutside);
    return () => document.removeEventListener('pointerdown', closeOnOutside);
  }, [open]);
  useEffect(() => { if (disabled) setOpen(false); }, [disabled]);
  useEffect(() => {
    const item = menu.current?.children[active];
    if (open && item) item.scrollIntoView({ block: 'nearest' });
  }, [active, open]);

  function show(focusSelected = false) {
    if (disabled || !options.length) return;
    const bounds = trigger.current.getBoundingClientRect();
    setOpenUp(window.innerHeight - bounds.bottom < 250 && bounds.top > 250);
    setActive(focusSelected ? selectedIndex : -1);
    setOpen(true);
  }
  function choose(index) {
    onChange(options[index].value);
    setOpen(false);
    trigger.current?.focus();
  }
  function onKeyDown(event) {
    if (disabled || !options.length) return;
    if (event.key === 'Escape' && open) {
      event.preventDefault();
      setOpen(false);
    } else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      if (!open) show(true);
      else setActive(index => index < 0 ? selectedIndex : (index + (event.key === 'ArrowDown' ? 1 : -1) + options.length) % options.length);
    } else if (event.key === 'Home' && open) {
      event.preventDefault(); setActive(0);
    } else if (event.key === 'End' && open) {
      event.preventDefault(); setActive(options.length - 1);
    } else if ((event.key === 'Enter' || event.key === ' ') && open) {
      event.preventDefault(); choose(active < 0 ? selectedIndex : active);
    }
  }

  return <div className={'styled-select' + (compact ? ' styled-select--compact' : '') + (openUp ? ' styled-select--up' : '')} ref={root} onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false); }}>
    <button ref={trigger} type="button" className="styled-select-trigger" role="combobox" aria-label={label} aria-haspopup="listbox" aria-expanded={open} aria-controls={open ? listId : undefined} aria-activedescendant={open && active >= 0 ? `${listId}-${active}` : undefined} disabled={disabled} onClick={() => open ? setOpen(false) : show()} onKeyDown={onKeyDown}>
      {compact && <BookOpen size={16} aria-hidden="true"/>}
      <span className="styled-select-value">{selected?.label || '请选择'}</span>
      <ChevronDown className="styled-select-chevron" size={17} aria-hidden="true"/>
    </button>
    {open && <div id={listId} ref={menu} className="styled-select-menu" role="listbox" aria-label={label}>
      {options.map((option, index) => <div id={`${listId}-${index}`} key={option.value} className={'styled-select-option' + (index === active ? ' is-active' : '')} role="option" aria-selected={option.value === value} onPointerDown={event => event.preventDefault()} onClick={() => choose(index)}>
        <span>{option.label}</span>{option.value === value && <i className="styled-select-selected-dot" aria-hidden="true"/>}
      </div>)}
    </div>}
  </div>;
}
