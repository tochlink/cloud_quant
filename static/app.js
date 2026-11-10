/* QTW 前端（无构建步骤的原生 JS 单页应用） */
const $ = (s, r = document) => r.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&#38;", "<": "&#60;", ">": "&#62;", '"': "&#34;", "'": "&#39;" }[c]));  // 用数字实体（与命名实体等价），避免推送时被解码
const S = { status: null, dash: null, signals: null, bt: null, page: "dashboard", rSearch: "", txPage: 0, selSym: null };

/* UI icons: filled paths from @douyinfe/semi-icons 2.104.0 (MIT, DouyinFE / Semi Design). */
const ICON = {
  home: '<path d="M2 11.4454C2 11.1619 2.12032 10.8917 2.33104 10.7021L11.331 2.60207C11.7113 2.2598 12.2887 2.2598 12.669 2.60207L21.669 10.7021C21.8797 10.8917 22 11.1619 22 11.4454V20C22 21.1046 21.1046 22 20 22H16C15.4477 22 15 21.5523 15 21V17C15 15.3432 13.6569 14 12 14C10.3431 14 9 15.3432 9 17V21C9 21.5523 8.55228 22 8 22H4C2.89543 22 2 21.1046 2 20V11.4454Z" fill="currentColor"/>',
  signals: '<path d="M2 4C2 2.89543 2.89543 2 4 2H9C10.1046 2 11 2.89543 11 4V9C11 10.1046 10.1046 11 9 11H4C2.89543 11 2 10.1046 2 9V4Z" fill="currentColor"/><path d="M2 15C2 13.8954 2.89543 13 4 13H9C10.1046 13 11 13.8954 11 15V20C11 21.1046 10.1046 22 9 22H4C2.89543 22 2 21.1046 2 20V15Z" fill="currentColor"/><path d="M13 15C13 13.8954 13.8954 13 15 13H20C21.1046 13 22 13.8954 22 15V20C22 21.1046 21.1046 22 20 22H15C13.8954 22 13 21.1046 13 20V15Z" fill="currentColor"/><path d="M13 4C13 2.89543 13.8954 2 15 2H20C21.1046 2 22 2.89543 22 4V9C22 10.1046 21.1046 11 20 11H15C13.8954 11 13 10.1046 13 9V4Z" fill="currentColor"/>',
  backtest: '<path d="M17 2C16.4477 2 16 2.44772 16 3V19H14V10C14 9.44772 13.5523 9 13 9H11C10.4477 9 10 9.44771 10 10V19H8V8C8 7.44772 7.55228 7 7 7H5C4.44772 7 4 7.44772 4 8V19H3C2.44772 19 2 19.4477 2 20V21C2 21.5523 2.44772 22 3 22H21C21.5523 22 22 21.5523 22 21V20C22 19.4477 21.5523 19 21 19H20V3C20 2.44772 19.5523 2 19 2H17Z" fill="currentColor"/>',
  positions: '<path fill-rule="evenodd" clip-rule="evenodd" d="M11 3.05493C6.50005 3.55237 3 7.36745 3 12C3 16.9706 7.02944 21 12 21C14.125 21 16.078 20.2635 17.6177 19.0319L11.1464 12.5607C11.0527 12.4669 11 12.3397 11 12.2071V3.05493ZM13 3.05493V11L20.9451 11C20.4839 6.82838 17.1716 3.51608 13 3.05493ZM14.4142 13L19.0319 17.6177C20.0676 16.3229 20.7532 14.7359 20.9451 13L14.4142 13ZM1 12C1 5.92487 5.92487 1 12 1C18.0751 1 23 5.92487 23 12C23 18.0751 18.0751 23 12 23C5.92487 23 1 18.0751 1 12Z" fill="currentColor"/>',
  trades: '<g opacity="0.99"><path fill-rule="evenodd" clip-rule="evenodd" d="M4 6.5C5.10457 6.5 6 5.60457 6 4.5C6 3.39543 5.10457 2.5 4 2.5C2.89543 2.5 2 3.39543 2 4.5C2 5.60457 2.89543 6.5 4 6.5ZM9.5 3C8.67157 3 8 3.67157 8 4.5C8 5.32843 8.67157 6 9.5 6H20.5C21.3284 6 22 5.32843 22 4.5C22 3.67157 21.3284 3 20.5 3H9.5ZM8 11.5C8 10.6716 8.67157 10 9.5 10H20.5C21.3284 10 22 10.6716 22 11.5C22 12.3284 21.3284 13 20.5 13H9.5C8.67157 13 8 12.3284 8 11.5ZM8 18.5C8 17.6716 8.67157 17 9.5 17H20.5C21.3284 17 22 17.6716 22 18.5C22 19.3284 21.3284 20 20.5 20H9.5C8.67157 20 8 19.3284 8 18.5ZM6 11.5C6 12.6046 5.10457 13.5 4 13.5C2.89543 13.5 2 12.6046 2 11.5C2 10.3954 2.89543 9.5 4 9.5C5.10457 9.5 6 10.3954 6 11.5ZM4 20.5C5.10457 20.5 6 19.6046 6 18.5C6 17.3954 5.10457 16.5 4 16.5C2.89543 16.5 2 17.3954 2 18.5C2 19.6046 2.89543 20.5 4 20.5Z" fill="currentColor"/></g>',
  risk: '<path fill-rule="evenodd" clip-rule="evenodd" d="M2.68218 3.79537L11.4254 1.17242C11.8002 1.05996 12.1999 1.05996 12.5747 1.17242L21.3071 3.79214C21.7206 3.91619 22.0073 4.28642 22.0115 4.71813C22.0373 7.34946 21.9785 16.4433 20.0001 19C18.0247 21.5528 13.6184 22.6574 12.3487 22.93C12.1172 22.9797 11.8824 22.9789 11.6512 22.9278C10.4032 22.6513 6.1216 21.5457 4.00009 19C1.86616 16.4394 1.91793 7.32182 1.97887 4.70618C1.9888 4.28004 2.2739 3.91786 2.68218 3.79537ZM12 4.00246V19.9983C12.0059 19.9994 12.009 20 12.009 20C12.009 20 15.9729 19.2727 17.5934 17.0909C19.2138 14.9091 18.9894 5.9091 18.9894 5.9091L12.009 4.00001L12 4.00246Z" fill="currentColor"/>',
  settings: '<path fill-rule="evenodd" clip-rule="evenodd" d="M7.99973 5.07197C7.19713 5.53535 6.20729 5.53113 5.40866 5.06092L5.1637 4.91669C4.55751 4.55978 3.77662 4.65563 3.34264 5.20927C2.69567 6.03462 2.17585 6.94251 1.79166 7.90124C1.53027 8.55354 1.83733 9.27693 2.449 9.62286L2.69407 9.76145C3.50107 10.2178 4.00002 11.0732 4.00002 12.0003C4.00002 12.9271 3.50145 13.7822 2.69492 14.2387L2.44842 14.3783C1.83596 14.725 1.52888 15.4497 1.79213 16.1024C1.98358 16.577 2.21048 17.044 2.47374 17.5C2.73723 17.9564 3.0285 18.3868 3.34416 18.7902C3.77773 19.3443 4.5588 19.4406 5.16498 19.0834L5.40839 18.9399C6.20714 18.4692 7.19739 18.4648 8.0003 18.9284C8.80291 19.3918 9.29417 20.2511 9.28627 21.1778L9.28386 21.4601C9.27787 22.1629 9.75107 22.7906 10.4468 22.8903C11.4692 23.0368 12.5154 23.0404 13.5537 22.8927C14.2499 22.7936 14.7231 22.1653 14.7169 21.462L14.7143 21.1785C14.7061 20.2514 15.1974 19.3916 16.0003 18.928C16.8029 18.4647 17.7927 18.4689 18.5914 18.9391L18.8363 19.0833C19.4425 19.4402 20.2234 19.3444 20.6574 18.7907C21.3044 17.9654 21.8242 17.0575 22.2084 16.0988C22.4698 15.4465 22.1627 14.7231 21.551 14.3772L21.306 14.2386C20.499 13.7822 20 12.9268 20 11.9997C20 11.0729 20.4986 10.2178 21.3051 9.76126L21.5516 9.62174C22.1641 9.27506 22.4712 8.55029 22.2079 7.89761C22.0165 7.42297 21.7896 6.95598 21.5263 6.50001C21.2628 6.04362 20.9715 5.61325 20.6559 5.20982C20.2223 4.65568 19.4412 4.55944 18.8351 4.91665L18.5916 5.06009C17.7929 5.53078 16.8026 5.53519 15.9997 5.07163C15.1971 4.60825 14.7059 3.74891 14.7138 2.82218L14.7162 2.53994C14.7222 1.83708 14.249 1.20945 13.5532 1.10973C12.5308 0.963214 11.4846 0.959581 10.4464 1.10733C9.75011 1.20641 9.27691 1.83473 9.28317 2.53798L9.28569 2.82154C9.29395 3.74862 8.80264 4.60841 7.99973 5.07197ZM14 15.4641C15.9132 14.3595 16.5687 11.9132 15.4641 9.99999C14.3595 8.08682 11.9132 7.43132 10 8.53589C8.08684 9.64046 7.43134 12.0868 8.53591 14C9.64048 15.9132 12.0868 16.5687 14 15.4641Z" fill="currentColor"/>',
  help: '<path fill-rule="evenodd" clip-rule="evenodd" d="M12 23C18.0751 23 23 18.0751 23 12C23 5.92487 18.0751 1 12 1C5.92487 1 1 5.92487 1 12C1 18.0751 5.92487 23 12 23ZM11.8281 14.6094C10.9688 14.6094 10.5391 14.0723 10.5391 13.3691C10.5391 12.3242 11.0566 11.6504 12.2676 10.7324C12.2894 10.7158 12.3111 10.6993 12.3326 10.6829C13.1573 10.0555 13.7324 9.61807 13.7324 8.82812C13.7324 7.93945 12.9023 7.42188 11.9746 7.42188C11.2129 7.42188 10.627 7.70508 10.168 8.30078C9.83594 8.64258 9.57227 8.82812 9.12305 8.82812C8.38086 8.82812 8 8.31055 8 7.71484C8 7.10938 8.3418 6.49414 8.87891 6.02539C9.60156 5.40039 10.7539 5 12.2773 5C14.9922 5 16.8965 6.33789 16.8965 8.64258C16.8965 10.3223 15.8906 11.1328 14.709 11.9531C13.9082 12.5391 13.5273 12.8809 13.2246 13.5742L13.2238 13.5756C12.8922 14.1609 12.638 14.6094 11.8281 14.6094ZM11.8086 18.7695C10.8711 18.7695 10.0996 18.1641 10.0996 17.2266C10.0996 16.2891 10.8711 15.6836 11.8086 15.6836C12.7461 15.6836 13.5078 16.2891 13.5078 17.2266C13.5078 18.1641 12.7461 18.7695 11.8086 18.7695Z" fill="currentColor"/>',
  play: '<path d="M5 2.90101C5 2.09583 5.90303 1.62081 6.56653 2.07697L19.8014 11.1759C20.3794 11.5733 20.3794 12.4267 19.8014 12.824L6.56653 21.923C5.90303 22.3792 5 21.9041 5 21.0989V2.90101Z" fill="currentColor"/>',
  stop: '<path d="M3 6C3 4.34315 4.34315 3 6 3H18C19.6569 3 21 4.34315 21 6V18C21 19.6569 19.6569 21 18 21H6C4.34315 21 3 19.6569 3 18V6Z" fill="currentColor"/>',
  dl: '<path fill-rule="evenodd" clip-rule="evenodd" d="M17.8395 8.05827C17.1837 5.16226 14.5944 3 11.5 3C7.91015 3 5 5.91015 5 9.5C5 10.0204 5.06115 10.5264 5.17665 11.0114C2.84229 11.1772 1 13.1234 1 15.5C1 17.9853 3.01469 20 5.49995 20H17C20.3137 20 23 17.3137 23 14C23 10.9712 20.7558 8.46659 17.8395 8.05827ZM11.6799 17.7333C11.8653 17.8878 12.1347 17.8878 12.3201 17.7333L17.4695 13.4421C17.6492 13.2924 17.5433 13 17.3095 13H14V9.5C14 9.22386 13.7761 9 13.5 9H10.5C10.2239 9 10 9.22386 10 9.5V13H6.69051C6.45669 13 6.35084 13.2924 6.53047 13.4421L11.6799 17.7333Z" fill="currentColor"/>',
  key: '<path fill-rule="evenodd" clip-rule="evenodd" d="M23 8.5C23 12.6421 19.6421 16 15.5 16C14.0696 16 12.7327 15.5996 11.5953 14.9047L11 15.5V19H7V23H2V19L8.91221 12.0878C8.33057 11.0221 8 9.79964 8 8.5C8 4.35786 11.3579 1 15.5 1C19.6421 1 23 4.35786 23 8.5ZM19 7.5C19 6.11929 17.8807 5 16.5 5C15.1193 5 14 6.11929 14 7.5C14 8.88071 15.1193 10 16.5 10C17.8807 10 19 8.88071 19 7.5Z" fill="currentColor"/>',
  x: '<path d="M17.6568 19.7782C18.2426 20.3639 19.1924 20.3639 19.7782 19.7782C20.3639 19.1924 20.3639 18.2426 19.7782 17.6568L14.1213 12L19.7782 6.34313C20.3639 5.75734 20.3639 4.8076 19.7782 4.22181C19.1924 3.63602 18.2426 3.63602 17.6568 4.22181L12 9.87866L6.34313 4.22181C5.75734 3.63602 4.8076 3.63602 4.22181 4.22181C3.63602 4.8076 3.63602 5.75734 4.22181 6.34313L9.87866 12L4.22181 17.6568C3.63602 18.2426 3.63602 19.1924 4.22181 19.7782C4.8076 20.3639 5.75734 20.3639 6.34313 19.7782L12 14.1213L17.6568 19.7782Z" fill="currentColor"/>',
  search: '<path fill-rule="evenodd" clip-rule="evenodd" d="M10.5 2C5.80558 2 2 5.80558 2 10.5C2 15.1944 5.80558 19 10.5 19C12.3054 19 13.9794 18.4371 15.356 17.4773L19.4393 21.5606C20.0251 22.1464 20.9749 22.1464 21.5606 21.5606C22.1464 20.9749 22.1464 20.0251 21.5606 19.4393L17.4773 15.356C18.4371 13.9794 19 12.3054 19 10.5C19 5.80558 15.1944 2 10.5 2ZM5 10.5C5 7.46243 7.46243 5 10.5 5C13.5376 5 16 7.46243 16 10.5C16 13.5376 13.5376 16 10.5 16C7.46243 16 5 13.5376 5 10.5Z" fill="currentColor"/>',
  bell: '<path d="M17.9999 9C17.9999 6.77641 16.7904 4.83534 14.9933 3.79886C14.8898 2.23579 13.5892 1 11.9999 1C10.4107 1 9.11006 2.23579 9.00658 3.79886C7.20952 4.83534 5.99995 6.77641 5.99995 9C5.99995 9 5.99995 11 5.49995 13C5.21672 14.1329 3.81039 15.9076 2.64425 17.2335C2.05586 17.9024 2.52326 19 3.41416 19H20.5857C21.4766 19 21.944 17.9024 21.3556 17.2335C20.1895 15.9076 18.7832 14.1329 18.4999 13C17.9999 11 17.9999 9 17.9999 9Z" fill="currentColor"/><path d="M15 20C15 21.6569 13.6569 23 12 23C10.3431 23 9 21.6569 9 20H15Z" fill="currentColor"/>',
  comment: '<path fill-rule="evenodd" clip-rule="evenodd" d="M23 11.5C23 5.70101 18.299 1 12.5 1C6.70101 1 2 5.70101 2 11.5C2 13.4179 2.51422 15.2157 3.4123 16.7631L2.08689 20.7393C1.83512 21.4946 2.52398 22.2269 3.29323 22.0218L7.70712 20.8448C9.14399 21.5832 10.7733 22 12.5 22C18.299 22 23 17.299 23 11.5ZM7.5 13C6.67157 13 6 12.3284 6 11.5C6 10.6716 6.67157 10 7.5 10C8.32843 10 9 10.6716 9 11.5C9 12.3284 8.32843 13 7.5 13ZM14 11.5C14 12.3284 13.3284 13 12.5 13C11.6716 13 11 12.3284 11 11.5C11 10.6716 11.6716 10 12.5 10C13.3284 10 14 10.6716 14 11.5ZM17.5 13C16.6716 13 16 12.3284 16 11.5C16 10.6716 16.6716 10 17.5 10C18.3284 10 19 10.6716 19 11.5C19 12.3284 18.3284 13 17.5 13Z" fill="currentColor"/>',
  chevron_right: '<path fill-rule="evenodd" clip-rule="evenodd" d="M7.43934 19.7957C6.85355 19.2099 6.85355 18.2601 7.43934 17.6744L13.0962 12.0175L7.43934 6.36065C6.85355 5.77486 6.85355 4.82511 7.43934 4.23933C8.02513 3.65354 8.97487 3.65354 9.56066 4.23933L16.2782 10.9568C16.864 11.5426 16.864 12.4924 16.2782 13.0782L9.56066 19.7957C8.97487 20.3815 8.02513 20.3815 7.43934 19.7957Z" fill="currentColor"/>',
  chevron_left: '<path fill-rule="evenodd" clip-rule="evenodd" d="M16.2782 4.23933C16.864 4.82511 16.864 5.77486 16.2782 6.36065L10.6213 12.0175L16.2782 17.6744C16.864 18.2601 16.864 19.2099 16.2782 19.7957C15.6924 20.3815 14.7426 20.3815 14.1569 19.7957L7.43934 13.0782C6.85355 12.4924 6.85355 11.5426 7.43934 10.9568L14.1569 4.23933C14.7426 3.65354 15.6924 3.65354 16.2782 4.23933Z" fill="currentColor"/>',
  info: '<path fill-rule="evenodd" clip-rule="evenodd" d="M12 23C18.0751 23 23 18.0751 23 12C23 5.92487 18.0751 1 12 1C5.92487 1 1 5.92487 1 12C1 18.0751 5.92487 23 12 23ZM14 7C14 8.10457 13.1046 9 12 9C10.8954 9 10 8.10457 10 7C10 5.89543 10.8954 5 12 5C13.1046 5 14 5.89543 14 7ZM9 10.75C9 10.3358 9.33579 10 9.75 10H12.5C13.0523 10 13.5 10.4477 13.5 11V16.5H14.25C14.6642 16.5 15 16.8358 15 17.25C15 17.6642 14.6642 18 14.25 18H9.75C9.33579 18 9 17.6642 9 17.25C9 16.8358 9.33579 16.5 9.75 16.5H10.5V11.5H9.75C9.33579 11.5 9 11.1642 9 10.75Z" fill="currentColor"/>',
  sidebar: '<path fill-rule="evenodd" clip-rule="evenodd" d="M5 2H19C20.6569 2 22 3.34315 22 5V19C22 20.6569 20.6569 22 19 22H5C3.34315 22 2 20.6569 2 19V5C2 3.34315 3.34315 2 5 2ZM6 4C5.44772 4 5 4.44772 5 5V19C5 19.5523 5.44772 20 6 20H9C9.55229 20 10 19.5523 10 19V5C10 4.44772 9.55229 4 9 4H6Z" fill="currentColor"/>',
  send: '<path d="M20.6027 2.13245L1.53504 8.48833C0.829806 8.72341 0.618511 9.61847 1.14416 10.1441L4.95675 13.9567C5.2771 14.2771 5.77281 14.3421 6.16489 14.1151L14.351 9.37577C14.5283 9.27312 14.7269 9.47176 14.6243 9.64907L9.88494 17.8351C9.65794 18.2272 9.7229 18.7229 10.0433 19.0433L13.8559 22.8559C14.3816 23.3815 15.2766 23.1702 15.5117 22.465L21.8676 3.39736C22.1282 2.6156 21.3844 1.87187 20.6027 2.13245Z" fill="currentColor"/>',
  alert: '<path fill-rule="evenodd" clip-rule="evenodd" d="M10.2268 2.3986L1.52616 19.0749C0.831449 20.4064 1.79747 22 3.29933 22H20.7007C22.2025 22 23.1686 20.4064 22.4739 19.0749L13.7732 2.3986C13.0254 0.965441 10.9746 0.965442 10.2268 2.3986ZM13.1415 14.0101C13.0603 14.5781 12.5739 15 12.0001 15C11.4263 15 10.9398 14.5781 10.8586 14.0101L10.2829 9.97992C10.1336 8.93495 10.9445 8.00002 12.0001 8.00002C13.0556 8.00002 13.8665 8.93495 13.7172 9.97992L13.1415 14.0101ZM13.5001 18.5C13.5001 19.3284 12.8285 20 12.0001 20C11.1716 20 10.5001 19.3284 10.5001 18.5C10.5001 17.6716 11.1716 17 12.0001 17C12.8285 17 13.5001 17.6716 13.5001 18.5Z" fill="currentColor"/>'
};
const ic = (k, cls = "") => `<svg viewBox="0 0 24 24" class="icon ${cls}" aria-hidden="true">${ICON[k] || ""}</svg>`;
function hydrateIcons(root = document) {
  root.querySelectorAll("[data-icon]").forEach((el) => {
    if (el.querySelector("svg.icon")) return;
    const svg = ic(el.dataset.icon, el.dataset.iconClass || "");
    if (!svg) return;
    if (el.matches("i, .icon-slot")) el.innerHTML = svg;
    else el.insertAdjacentHTML("afterbegin", svg);
  });
}
const NAV = [
  ["dashboard", "home", "总览", "总览"], ["signals", "signals", "信号", "信号 / 进出场"], ["backtest", "backtest", "回测", "回测"], ["positions", "positions", "持仓", "持仓"],
  ["trades", "trades", "成交", "成交"], ["risk", "risk", "风控", "风控 / 自动交易"], ["settings", "settings", "设置", "行情源 / API / 实盘"], ["help", "help", "帮助", "帮助"],
];
const COIN = { BTC: "#f7931a", ETH: "#627eea", BNB: "#e0a800", SOL: "linear-gradient(135deg,#9945ff,#14f195)", XRP: "#23292f", ADA: "#0033ad", DOGE: "#c2a633", AVAX: "#e84142", LTC: "#345d9d", LINK: "#2a5ada", TRX: "#d8222a", DOT: "#e6007a" };
function coin(sym, cls = "") {
  const b = sym.replace(/USDT$/, "");
  let bg = COIN[b];
  if (!bg) { let h = 0; for (const c of b) h = (h * 31 + c.charCodeAt(0)) % 360; bg = `hsl(${h} 55% 45%)`; }
  return `<div class="coin ${cls}" style="background:${bg}">${esc(b.slice(0, 4))}</div>`;
}
const f2 = (x, d = 2) => (x == null || !isFinite(x) ? "—" : Number(x).toLocaleString("zh-CN", { minimumFractionDigits: d, maximumFractionDigits: d }));
const fp = (x, d = 6) => (x == null || !isFinite(x) ? "—" : Number(x).toPrecision(d).replace(/\.?0+$/, ""));
const pct = (x, d = 2) => (x == null || !isFinite(x) ? "—" : (x * 100).toFixed(d) + "%");
const sgn = (x, d = 2) => { if (x == null || !isFinite(x)) return "—"; if (Math.abs(x) < 0.5 * 10 ** -d) x = 0; return (x > 0 ? "+" : x < 0 ? "" : "±") + f2(x, d); };
const cls = (x) => (x > 0 ? "pos" : x < 0 ? "neg" : "");
const t = (iso) => (iso ? PT.short(iso) : "—");
const tFull = (iso, sec) => (iso ? PT.full(iso, sec) : "—");
/* 后端文案里的 ISO / 旧 PST / CST+8 时间统一改写成 “MM-DD HH:mm 北京时间” */
const ptText = (s) => String(s ?? "")
  .replace(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})/g, (m) => PT.short(m))
  .replace(/\d{4}-\d{2}-\d{2} \d{2}:\d{2}(?::\d{2})? P[SD]T/g, (m) => {
    const d = new Date(m.replace(" PST", " GMT-0800").replace(" PDT", " GMT-0700"));
    return isNaN(d) ? m : PT.short(d);
  })
  .replace(/\d{4}-(\d{2})-(\d{2}) (\d{2}):(\d{2})(?::\d{2})? (?:CST\+8|北京时间)/g, "$1-$2 $3:$4 北京时间");
const sideCn = (s) => ({ long: "做多", short: "做空", flat: "空仓" }[s] || s);
const mktCn = (m) => ({ spot: "现货", perp: "USDT 永续" }[m] || m);
const VN = { okx: "OKX", gate: "Gate.io" };
const base = (sym) => sym.replace(/USDT$/, "");
const pxOk = (x) => x != null && isFinite(Number(x)) && Number(x) > 0;
const fpPx = (x) => (pxOk(x) ? fp(x) : "—");
const tCompact = (iso) => { if (!iso) return "—"; return PT.short(iso).replace(/ 北京时间$/, ""); };
function fqty(x) {
  if (x == null || !isFinite(Number(x))) return "—";
  const n = Number(x), a = Math.abs(n);
  const d = a >= 100 ? 2 : a >= 1 ? 4 : 5;
  return n.toLocaleString("zh-CN", { minimumFractionDigits: 0, maximumFractionDigits: d });
}
const STALE_SEC = 20;
S.pg = S.pg || {};
function quoteFresh(q) {
  if (!q || !pxOk(q.price)) return false;
  if (q.age_sec != null && isFinite(q.age_sec) && q.age_sec > STALE_SEC) return false;
  return true;
}
function liveQuote(sym, mkt) {
  return (S.live && S.live.prices && S.live.prices[sym] && quoteFresh(S.live.prices[sym][mkt])) ? S.live.prices[sym][mkt] : null;
}
function ageSec(isoStr) {
  if (!isoStr) return null;
  const ms = Date.parse(isoStr);
  return isFinite(ms) ? (Date.now() - ms) / 1000 : null;
}
function currentPx(sym, mkt, fallback, fallbackTime) {
  const q = liveQuote(sym, mkt);
  if (q) return Number(q.price);
  if (pxOk(fallback)) {
    const age = ageSec(fallbackTime);
    if (age != null && age > STALE_SEC) return null;
    return Number(fallback);
  }
  return null;
}
function posMark(p) {
  const m = p.market && p.market !== "-" ? p.market : "spot";
  return currentPx(p.symbol, m, p.mark_price, p.mark_time);
}
function posUpnl(p, mark) {
  const e = p.entry_price, m = mark, q = p.qty;
  if (!pxOk(e) || !pxOk(m)) return { usdt: null, pct: null };
  const dir = p.side === "short" ? -1 : 1;
  const pctV = dir * (Number(m) / Number(e) - 1);
  const usdt = (q != null && isFinite(Number(q))) ? dir * Number(q) * (Number(m) - Number(e)) : null;
  return { usdt, pct: pctV };
}
function fmtPnl(pnl, stacked) {
  if (pnl.usdt == null && pnl.pct == null) return "—";
  const a = pnl.usdt == null ? "—" : sgn(pnl.usdt);
  if (pnl.pct == null) return a;
  const b = (pnl.pct >= 0 ? "+" : "") + pct(pnl.pct);
  return stacked ? `${a}\n(${b})` : `${a}（${b}）`;
}
function setTextFlash(el, text) {
  if (!el || el.textContent === text) return;
  el.textContent = text;
  el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash");
}
function updateLiveCells() {
  document.querySelectorAll("[data-live='px']").forEach((el) => {
    const px = currentPx(el.dataset.sym, el.dataset.mkt || "spot", el.dataset.mark, el.dataset.markTime);
    const pre = el.dataset.pxPrefix || "";
    setTextFlash(el, pre ? (pxOk(px) ? pre + fpPx(px) : "—") : fpPx(px));
  });
  document.querySelectorAll("[data-live='pnl']").forEach((el) => {
    const px = currentPx(el.dataset.sym, el.dataset.mkt || "spot", el.dataset.mark, el.dataset.markTime);
    let pnl = posUpnl({ entry_price: el.dataset.entry, qty: el.dataset.qty, side: el.dataset.side }, px);
    const fee = Number(el.dataset.fee || 0);
    if (fee && pnl.usdt != null) {
      const net = pnl.usdt - fee;
      const e = Number(el.dataset.entry), q = Number(el.dataset.qty);
      pnl = { usdt: net, pct: (pxOk(e) && q) ? net / (e * q) : pnl.pct };
    }
    const txt = fmtPnl(pnl, el.dataset.stacked === "1");
    const target = el.querySelector("[data-live-pnl-txt]") || el;
    setTextFlash(target, txt);
    el.classList.toggle("pos", pnl.usdt != null && pnl.usdt > 0);
    el.classList.toggle("neg", pnl.usdt != null && pnl.usdt < 0);
  });
  document.querySelectorAll("[data-live='weight']").forEach((el) => {
    const px = currentPx(el.dataset.sym, el.dataset.mkt || "spot", el.dataset.mark, el.dataset.markTime);
    const eq = S.dash && S.dash.equity, q = Number(el.dataset.qty);
    const w = (pxOk(px) && eq && q) ? (Math.abs(q * px) / eq) : null;
    setTextFlash(el, pct(w, 1));
  });
  document.querySelectorAll("[data-px]").forEach((el) => {
    const [sym, m] = el.dataset.px.split(":");
    const q = liveQuote(sym, m);
    if (q) setTextFlash(el, fp(q.price));
  });
}
function pgState(key, total, size) {
  size = Math.max(1, size | 0);
  const st = S.pg[key] || { i: 0 };
  if (st._fit) size = Math.max(1, st._fit);
  const pages = Math.max(1, Math.ceil((total || 0) / size));
  st.n = size;
  if (st.i >= pages) st.i = pages - 1;
  if (st.i < 0) st.i = 0;
  S.pg[key] = st;
  const start = st.i * size;
  return { i: st.i, n: size, pages, start, end: Math.min(total || 0, start + size), total: total || 0 };
}
function pagerHtml(key, st) {
  if (!st.total) return "";
  return `<div class="pager" data-pg="${key}">
    <button type="button" class="pager-btn" data-d="-1" ${st.i <= 0 ? "disabled" : ""} aria-label="上一页">上一页</button>
    <span class="pager-ind">第 ${st.i + 1} / ${st.pages} 页 · ${st.total} 条</span>
    <button type="button" class="pager-btn" data-d="1" ${st.i >= st.pages - 1 ? "disabled" : ""} aria-label="下一页">下一页</button>
  </div>`;
}
function bindPager(key, redraw) {
  const bar = document.querySelector(`[data-pg="${key}"]`);
  if (!bar) return;
  bar.querySelectorAll("[data-d]").forEach((b) => (b.onclick = () => { S.pg[key].i += +b.dataset.d; redraw(); }));
}
function bindTabs(stateKey, rootSel, initial) {
  const root = $(rootSel); if (!root) return;
  const go = (tab) => {
    S[stateKey] = tab;
    root.querySelectorAll(".set-nav [data-tab]").forEach((b) => {
      const on = b.dataset.tab === tab;
      b.classList.toggle("on", on);
      b.setAttribute("aria-selected", on ? "true" : "false");
    });
    root.querySelectorAll(".set-pane").forEach((p) => p.classList.toggle("on", p.dataset.pane === tab));
  };
  root.querySelectorAll(".set-nav [data-tab]").forEach((b) => (b.onclick = () => go(b.dataset.tab)));
  const first = root.querySelector(".set-nav [data-tab]");
  go(initial || S[stateKey] || (first && first.dataset.tab));
}
function fitRows(host, rowH, extraH = 0, min = 3) {
  if (!host) return min;
  const h = host.clientHeight || 0;
  return Math.max(min, Math.floor(Math.max(0, h - extraH) / rowH) || min);
}
function tightenIfOverflow(host, key, redraw) {
  if (!host || host.clientHeight <= 0) return;
  if (host.scrollHeight > host.clientHeight + 6) {
    const st = S.pg[key];
    if (st && st.n > 1 && st._fit !== st.n - 1) { st._fit = st.n - 1; redraw(); }
  }
}
function refitByActualRows(host, key, rowSel, redraw, min = 2) {
  const row = host && host.querySelector(rowSel);
  if (!host || !row || host.clientHeight <= 0) return;
  const rowH = row.getBoundingClientRect().height;
  if (!(rowH > 8)) return;
  const head = host.querySelector("thead");
  const headH = head ? head.getBoundingClientRect().height : 0;
  const n = Math.max(min, Math.floor((host.clientHeight - headH - 12) / rowH));
  const st = S.pg[key];
  if (!st || n === st.n) return;
  if (n < st.n && host.scrollHeight <= host.clientHeight + 2) return;
  st._fit = n;
  redraw();
}
function relayoutPagers() {
  const page = $("#page"), rail = $("#rList");
  const sig = `${page?.clientWidth||0}x${page?.clientHeight||0}:${rail?.clientWidth||0}x${rail?.clientHeight||0}`;
  if (S._fitSig === sig) return;
  S._fitSig = sig;
  Object.keys(S.pg || {}).forEach((k) => { if (S.pg[k]) S.pg[k]._fit = null; });
  if (S.page === "signals") renderSigList();
  else if (S.page === "trades" && S.trades) renderTradesPage(false);
  else if (S.page === "positions") renderPosTable();
  else if (S.page === "dashboard") renderDashTx();
  else if (S.page === "backtest") renderBtTrades();
  renderRight();
}

function toast(msg, err) { const el = $("#toast"); el.textContent = msg; el.className = "toast show" + (err ? " err" : ""); clearTimeout(el._t); el._t = setTimeout(() => (el.className = "toast"), 4200); }
async function api(path, opt = {}) {
  const o = { method: opt.method || "GET", headers: { "Content-Type": "application/json" } };
  if (opt.body !== undefined) o.body = JSON.stringify(opt.body);
  const r = await fetch(path, o);
  let j = null; try { j = await r.json(); } catch (_) {}
  if (!r.ok) throw new Error((j && (j.detail || j.message)) || `HTTP ${r.status}`);
  return j;
}
function modal(html, onMount) { const card = $("#modalCard"); card.classList.remove("sig-detail"); S.sigModalSym = null; card.innerHTML = html; $("#modal").classList.remove("hidden"); onMount && onMount(card); const f = card.querySelector("[data-ok], .btn"); f && f.focus(); }
function closeModal() { $("#modal").classList.add("hidden"); $("#modalCard").classList.remove("sig-detail"); S.sigModalSym = null; }
$("#modal").addEventListener("click", (e) => { if (e.target.id === "modal") closeModal(); });
function confirmBox(title, body, okText, danger) {
  return new Promise((res) => modal(`<h3>${title}</h3><div class="note" style="font-size:13px">${body}</div><div class="acts"><button class="btn ghost" data-x>取消</button><button class="btn ${danger ? "danger" : ""}" data-ok>${okText}</button></div>`,
    (m) => { m.querySelector("[data-x]").onclick = () => { closeModal(); res(false); }; m.querySelector("[data-ok]").onclick = () => { closeModal(); res(true); }; }));
}
/* 带感叹号的说明：鼠标悬停 / 键盘聚焦时展开格式化说明 */
const infoTip = (html, label = "说明") => `<span class="info" tabindex="0" role="button" aria-label="${label}">${ic("info")}<span class="pop" role="tooltip">${html}</span></span>`;

/* ---------- 外壳 ---------- */
function renderNav() {
  $("#sidebar").innerHTML = NAV.map(([id, icon, label, tip]) => `<button class="nav-item ${S.page === id ? "active" : ""}" data-go="${id}" aria-label="${label}" ${S.page === id ? 'aria-current="page"' : ""}>${ic(icon)}<span class="tip">${tip || label}</span></button>`).join("");
  $("#sidebar").querySelectorAll("[data-go]").forEach((b) => (b.onclick = () => (location.hash = "#/" + b.dataset.go)));
}
function greet() {
  const h = PT.hour();
  const g = h < 5 ? "夜深了" : h < 11 ? "早上好" : h < 13 ? "中午好" : h < 18 ? "下午好" : "晚上好";
  S.greeting = `${g}，kean`;
  if (S.page === "dashboard") $("#greet").textContent = S.greeting;
}
function renderTitle() {
  const n = NAV.find((x) => x[0] === S.page);
  $("#greet").textContent = S.page === "dashboard" ? S.greeting || "你好，kean" : n[2];
  $("#pageSub").textContent = (S.page === "dashboard" ? "" : `${S.greeting || "kean"} · `) + SUBS[S.page];
}
function renderMode() {
  const st = S.status; if (!st) return;
  const live = st.mode === "live", v = st.settings.venue;
  const b = $("#modeBadge");
  b.className = "stat-pill " + (live ? "live" : "paper");
  b.querySelector("span").textContent = live ? `实盘已开启 · ${VN[v]}` : "纸面模式";
  b.title = live ? "实盘已开启：订单会真实发送到交易所。点击查看运行状态" : "纸面模式：只在本地账本记账，不向交易所下单。点击查看运行状态";
  $("#shell").classList.toggle("live-on", live);
  const hasPos = !!(S.dash && S.dash.positions && S.dash.positions.length);
  document.querySelectorAll("[data-venue]").forEach((x) => {
    x.classList.toggle("on", x.dataset.venue === v); x.setAttribute("aria-pressed", x.dataset.venue === v);
    x.disabled = live || (hasPos && x.dataset.venue !== v);
    x.title = live ? "实盘开启时不能在这里切换交易所，请先到「设置」关闭实盘"
      : hasPos && x.dataset.venue !== v ? `有 ${S.dash.positions.length} 个纸面持仓，请先平仓或重置后再切换行情源`
      : `使用 ${VN[x.dataset.venue]} 官方公共行情（仍为纸面）`;
  });
  const w = st.worker;
  $("#bellDot").className = "dot" + (w.last_error ? " warn" : "");
  $("#bellDot").style.display = w.running || w.last_error ? "" : "none";
  renderLivePill();
}
/* 行情源切换：只改公共行情来源，绝不开启实盘 */
async function setVenue(v) {
  if (!S.status || v === S.status.settings.venue) return;
  if (S.status.mode === "live") { toast("实盘开启中：请先到「设置」关闭实盘，再切换交易所", true); return; }
  const nPos = S.dash?.positions?.length || 0;
  if (nPos) { toast(`当前有 ${nPos} 个纸面持仓，不能切换行情源。请先紧急停止平仓或重置账本。`, true); return; }
  try {
    await api("/api/settings", { method: "PUT", body: { venue: v } });
    toast(`行情源已切换为 ${VN[v]} · 仍为纸面模式，不下真实单`);
    S.signals = null; S.chart = null;
    await refreshAll();
    if (!["dashboard", "positions"].includes(S.page)) await PAGES[S.page]();
    api("/api/signals").then((r) => { S.signals = r; renderRight(); if (S.page === "dashboard") pageDashboard(); }).catch(() => {});
  } catch (e) { toast("切换失败：" + e.message, true); }
}
document.querySelectorAll("[data-venue]").forEach((b) => (b.onclick = () => setVenue(b.dataset.venue)));
async function runCycle(btn) {
  const b = btn || $("#runNowBtn"), orig = b.innerHTML; b.disabled = true; b.innerHTML = '<span class="spin"></span><span>运行中…</span>';
  try { const r = await api("/api/cycle", { method: "POST" }); toast(r.events.length ? r.events.join("；") : "已跑完一轮：无需调仓"); await refreshAll(); }
  catch (err) { toast("执行失败：" + err.message, true); }
  finally { b.disabled = false; b.innerHTML = orig; }
}
$("#runNowBtn").onclick = (e) => runCycle(e.currentTarget);
async function killSwitch() {
  if (!(await confirmBox("紧急停止", "将立即：<br>① 停止后台自动交易；② 关闭实盘开关并切回纸面；③ 按最新公共价格平掉<b>全部纸面持仓</b>。<br><br>本操作不会向交易所发送任何订单。", "立即停止并平仓", true))) return;
  try { const r = await api("/api/kill", { method: "POST" }); toast(r.events.length ? "已平仓：" + r.events.join("；") : "已停止，当前无持仓"); await refreshAll(); if (S.page === "risk") pageRisk(); }
  catch (e) { toast(e.message, true); }
}
$("#killBtn").onclick = killSwitch;
$("#alertGo").onclick = () => { setRail(false); location.hash = "#/signals"; };
const setRail = (open) => { $("#shell").classList.toggle("rail-open", open); $("#railBtn").setAttribute("aria-expanded", open); };
$("#railBtn").onclick = () => setRail(!$("#shell").classList.contains("rail-open"));
$("#railClose").onclick = () => setRail(false);
$("#railBackdrop").onclick = () => setRail(false);
document.addEventListener("keydown", (e) => { if (e.key === "Escape") { setRail(false); closeModal(); } });
$("#rSearchBtn").onclick = () => { const i = $("#rSearch"); i.classList.toggle("hidden"); if (!i.classList.contains("hidden")) i.focus(); else { i.value = ""; S.rSearch = ""; renderRight(); } };
$("#rSearch").oninput = (e) => { S.rSearch = e.target.value.trim().toUpperCase(); renderRight(); };
$("#bellBtn").onclick = () => showStatusModal();
$("#modeBadge").onclick = () => showStatusModal();
$("#noticeBtn").onclick = () => showNotices();
function goSignal(sym, mkt) {
  S.selSym = sym; if (mkt && mkt !== "-") S.chartMkt = mkt;
  setRail(false);
  if (S.page === "signals") { selectSignal(sym); } else location.hash = "#/signals";
}

function showStatusModal() {
  const st = S.status, w = st.worker;
  modal(`<h3>运行状态</h3><dl class="kvlist">
    <dt>交易模式</dt><dd><b class="${st.mode === "live" ? "neg" : "pos"}">${st.mode === "live" ? "实盘（会真实下单）" : "纸面（只记账，不下单）"}</b></dd>
    <dt>行情源</dt><dd>${VN[st.settings.venue]} 官方公共行情</dd>
    <dt>自动交易</dt><dd><b>${w.running ? "运行中" : "已停止"}</b>${w.running ? ` · 每 ${st.settings.worker.interval_sec} 秒 · 下次约 ${w.next_run_in_sec ?? "—"} 秒后` : ""}</dd>
    <dt>上次执行</dt><dd>${tFull(w.last_run, true)}${w.last_error ? `<br><span class="neg">上次错误：${esc(w.last_error)}</span>` : ""}</dd>
    <dt>实盘闸门</dt><dd>${st.live_gate_open ? '<b class="neg">已打开</b>' : "关闭"}${st.live_block_reasons.length ? `<div class="muted" style="margin-top:4px">未满足：${st.live_block_reasons.map(esc).join("；")}</div>` : ""}</dd>
  </dl><div class="acts"><button class="btn ghost" data-close>关闭</button><button class="btn" data-risk>去风控页</button></div>`,
  (m) => { m.querySelector("[data-close]").onclick = closeModal; m.querySelector("[data-risk]").onclick = () => { closeModal(); location.hash = "#/risk"; }; });
}
function showNotices() {
  const r = S.dash?.worker?.last_result;
  const ev = r ? [...(r.events || []), ...Object.entries(r.errors || {}).map(([k, v]) => `${k}：${v}`)] : [];
  modal(`<h3>系统消息</h3><div class="note" style="font-size:13px;line-height:1.8">${ev.length ? ev.map((x) => "• " + esc(ptText(x))).join("<br>") : "最近一次自动周期没有新消息。"}
  <br><br>提示：这是系统化纸面 / 研究工具，不构成投资建议；实盘交易可能亏损全部本金。</div><div class="acts"><button class="btn" data-close>知道了</button></div>`, (m) => (m.querySelector("[data-close]").onclick = closeModal));
}

/* ---------- 右侧面板 ---------- */
const CHEV = ic("chevron_right", "chev");
function renderRight() {
  const d = S.dash; if (!d) return;
  const q = S.rSearch;
  let html = "";
  if (d.positions.length) {
    $("#rTitle").textContent = "持仓";
    $("#railBtnLbl").textContent = `持仓 ${d.positions.length}`;
    $("#rSub").textContent = `${d.positions.length} 个纸面持仓 · 点击查看该币信号与 K 线`;
    const allPos = d.positions.filter((p) => !q || p.symbol.includes(q)).sort((a, b) => b.weight - a.weight);
    const stP = pgState("rail", allPos.length, fitRows($("#rList"), 82, 0, 2));
    html = allPos.slice(stP.start, stP.end).map((p) => {
      const mark = posMark(p), pnl = posUpnl(p, mark);
      const live = `data-sym="${p.symbol}" data-mkt="${p.market}" data-entry="${p.entry_price}" data-qty="${p.qty}" data-side="${p.side}" data-mark="${p.mark_price ?? ""}" data-mark-time="${esc(p.mark_time || "")}"`;
      return `<button class="r-row" data-sym="${p.symbol}" data-mkt="${p.market}" title="查看 ${base(p.symbol)} 的信号与 K 线">${coin(p.symbol)}<div class="r-mid"><div class="nm">${base(p.symbol)}<span class="muted" style="font-weight:500"> /USDT</span></div>
      <div class="ds"><span class="side-tag ${p.side}">${sideCn(p.side)}</span> ${mktCn(p.market)}</div>
      <div class="px-line">入仓价 ${fpPx(p.entry_price)}</div>
      <div class="px-line">当前价 <b class="num" data-live="px" ${live}>${fpPx(mark)}</b></div>
      <div class="pnl-line ${cls(pnl.usdt)}" data-live="pnl" data-prefix="盈亏 " ${live}>盈亏 <span data-live-pnl-txt>${fmtPnl(pnl)}</span></div></div>
      <div class="rt"><span data-live="weight" ${live}>${pct(p.weight, 1)}</span><div class="ds">权重</div></div>${CHEV}</button>`;
    }).join("");
    S._railPager = stP;
  } else {
    $("#rTitle").textContent = "关注币种";
    $("#railBtnLbl").textContent = "关注币种";
    $("#rSub").textContent = "当前空仓 · 点击查看信号与 K 线";
    const rows = S.signals?.rows || S.status.settings.symbols.map((s) => ({ symbol: s }));
    const allWatch = rows.filter((r) => !q || r.symbol.includes(q));
    const stW = pgState("rail", allWatch.length, fitRows($("#rList"), 56, 0, 4));
    html = allWatch.slice(stW.start, stW.end).map((r) => {
      const m = r.market && r.market !== "-" ? r.market : "spot";
      const v = currentPx(r.symbol, m, r.ref_price, r.ref_price_time);
      return `<button class="r-row" data-sym="${r.symbol}" data-mkt="${r.signal_market || ""}" title="查看 ${base(r.symbol)} 的信号与 K 线">${coin(r.symbol)}<div><div class="nm">${base(r.symbol)}<span class="muted" style="font-weight:500"> /USDT</span></div>
      <div class="ds">${r.advice ? `<span class="side-tag ${r.side}">${sideCn(r.side)}</span> ${r.market !== "-" ? r.market_cn : ""}` : r.error ? "数据不可用" : "加载中…"}</div></div>
      <div class="rt num"><span data-live="px" data-sym="${r.symbol}" data-mkt="${m}" data-mark="${r.ref_price ?? ""}" data-mark-time="${esc(r.ref_price_time || "")}">${fpPx(v)}</span><div class="ds">${m === "perp" ? "永续标记" : "现货最新"}</div></div>${CHEV}</button>`;
    }).join("");
    S._railPager = stW;
  }
  $("#rList").innerHTML = html || '<div class="empty">无匹配</div>';
  $("#rList").querySelectorAll("[data-sym]").forEach((el) => (el.onclick = () => goSignal(el.dataset.sym, el.dataset.mkt)));
  const rp = $("#rPager");
  if (rp) { rp.innerHTML = S._railPager ? pagerHtml("rail", S._railPager) : ""; bindPager("rail", renderRight); }
  if (S._railPager) {
    tightenIfOverflow($("#rList"), "rail", renderRight);
    requestAnimationFrame(() => refitByActualRows($("#rList"), "rail", ".r-row", renderRight, 2));
  }
  const st = S.status;
  let msg;
  if (st.mode === "live") msg = `⚠️ 实盘已开启<small>订单将真实发送到 ${VN[st.settings.venue]}，随时可按“紧急停止”。</small>`;
  else if (d.max_drawdown < -0.1) msg = `纸面回撤已达 ${pct(d.max_drawdown, 1)}<small>请检查风控参数，必要时紧急停止。</small>`;
  else if (S.signals) {
    const rows = S.signals.rows.filter((r) => !r.error);
    const L = rows.filter((r) => r.signal > 0).length, Sh = rows.filter((r) => r.signal < 0).length, F = rows.length - L - Sh;
    const pend = rows.filter((r) => r.state === "entry_pending").length;
    msg = `最新信号：${L} 多 · ${Sh} 空 · ${F} 空仓<small>${pend ? `${pend} 个等待入场 · ` : ""}基于 ${t(rows[0]?.as_of)} 收盘 K 线</small>`;
  } else msg = `${st.worker.running ? "自动交易运行中" : "自动交易未开启"}<small>默认纸面模式，可在风控页开启。</small>`;
  $("#rAlertText").innerHTML = msg;
}

/* ---------- 总览 ---------- */
const HEROWAVE = `<svg class="deco" viewBox="0 0 600 220" preserveAspectRatio="none"><path d="M330 0H600V90C540 140 500 40 440 80S360 70 330 0Z" fill="#5ee0d6" opacity=".22"/><circle cx="590" cy="210" r="120" fill="#6c5ce7" opacity=".35"/></svg>`;
function txRow(f) {
  const pnl = Number(f.realized_pnl_usdt), open = f.action === "open", buy = f.side === "buy";
  const title = `${base(f.symbol)} ${open ? "开" : "平"}${f.market === "spot" ? "多" : "空"}`;
  const amt = open ? `<b class="num">${f2(f.notional_usdt)}</b><small>名义 USDT</small>` : `<b class="num ${cls(pnl)}">${sgn(pnl)}</b><small>已实现 USDT</small>`;
  return `<button class="tx" data-sym="${f.symbol}" data-mkt="${f.market}" title="查看 ${base(f.symbol)} 的信号与 K 线">${coin(f.symbol)}
    <div class="tx-mid"><div class="ttl">${esc(title)} <span class="muted">· ${mktCn(f.market)}</span></div><div class="ds">${t(f.time)} · 价格 ${fp(f.price)} · ${esc(ptText(f.reason))}</div></div>
    <span class="badge ${buy ? "buy" : "sell"}">${buy ? "买入" : "卖出"}</span><div class="amt">${amt}</div>${CHEV}</button>`;
}
function sigRowAsTx(r) {
  return `<button class="tx" data-sym="${r.symbol}" data-mkt="${r.signal_market || ""}" title="查看 ${base(r.symbol)} 的信号与 K 线">${coin(r.symbol)}
    <div class="tx-mid"><div class="ttl">${base(r.symbol)} <span class="muted">· ${r.market !== "-" ? r.market_cn : "—"}</span></div><div class="ds">${esc(ptText(r.entry_timing))}</div></div>
    <span class="badge ${r.side}">${sideCn(r.side)}</span><div class="amt">${r.target_notional_usdt ? `<b class="num">${f2(r.target_notional_usdt)}</b><small>建议名义</small>` : "<b>—</b>"}</div>${CHEV}</button>`;
}
function pageDashboard() {
  const d = S.dash, st = S.status, v = st.settings.venue;
  const fills = d.recent_fills.slice(0, 6);
  const sigs = (S.signals?.rows || []).filter((r) => !r.error).slice(0, 5);
  const list = fills.length ? fills.map(txRow).join("") : sigs.length ? sigs.map(sigRowAsTx).join("") : '<div class="empty">尚无成交。点击右上角「跑一轮」执行一次系统化周期。</div>';
  const longN = d.positions.filter((p) => p.side === "long").reduce((a, p) => a + p.notional, 0);
  const shortN = d.positions.filter((p) => p.side === "short").reduce((a, p) => a + p.notional, 0);
  const cash = Math.abs(d.cash_free) < 0.005 ? 0 : d.cash_free;
  const realizedPnl = d.total_pnl - d.unrealized;
  const eqs = d.ledger.map((x) => x.equity); if (eqs.length) eqs.push(d.equity);
  const w = d.worker || st.worker;
  const curDD = d.drawdown.length ? d.drawdown[d.drawdown.length - 1] : 0;
  const cum = d.pnl_by_trade.reduce((a, x) => (a.push((a.at(-1) || 0) + x), a), []);
  const stat = (lbl, val, sub, c = "", extra = "") => `<div class="stat ${extra}"><div class="s-lbl">${lbl}</div><div class="s-val num ${c}">${val}</div><div class="s-sub">${sub}</div></div>`;
  $("#page").innerHTML = `
  <div class="fit dash">
    <section class="hero">${HEROWAVE}
      <div class="hero-main">
        <div class="h-lbl">纸面权益 · USDT</div>
        <div class="h-val num">${f2(d.equity)}</div>
        <div class="h-chg"><span class="chg ${d.total_pnl >= 0 ? "up" : "down"}">${sgn(d.total_pnl)} · ${d.total_return >= 0 ? "+" : ""}${pct(d.total_return)}</span><span>相对起始 ${f2(d.starting_equity, 0)} USDT</span></div>
      </div>
      <div class="hero-spark">${MiniCharts.spark(eqs)}<div class="cap">账本权益走势 · ${d.ledger.length} 个记录点</div></div>
    </section>
    <section class="stats">
      ${stat("可用现金", f2(cash), cash < 0 ? `<span class="explain">空头价格上涨后，持仓名义（${f2(d.gross, 0)}）已超过权益。这是亏损空头的正常记账，不是错误；回落前不会再开新仓。</span>` : "权益 − 持仓名义，可用于新开仓", cash < 0 ? "neg" : "", cash < 0 ? "warn" : "")}
      ${stat("持仓敞口", f2(d.gross, 0), `${d.positions.length} 个持仓 · 净敞口 ${sgn(d.net, 0)}`)}
      ${stat("未实现盈亏", sgn(d.unrealized), `已实现 ${sgn(realizedPnl)}（含手续费）`, cls(d.unrealized))}
    </section>
    <section class="panel tx-panel">
      <div class="sec-title"><div><h3>${fills.length ? "最近成交" : "当前信号预览"}</h3><div class="note">${fills.length ? `本周 ${d.week.fills} 笔 · 已实现 <span class="pos">+${f2(d.week.gains)}</span> / <span class="neg">${f2(d.week.losses)}</span> USDT · 点击查看该币 K 线` : "尚无成交 · 以下为系统化信号"}</div></div>
        <button class="link" data-go="${fills.length ? "trades" : "signals"}">${fills.length ? "全部成交" : "全部信号"} →</button></div>
      <div class="tx-list" id="dashTx">${list}</div>
    </section>
    <section class="facts">
      <div class="tile"><div class="tt">最大回撤</div><div class="tv num ${d.max_drawdown < -0.1 ? "neg" : ""}">${pct(d.max_drawdown, 1)}</div><div class="tu">当前距高点 ${pct(curDD, 1)}</div><div class="tc">${MiniCharts.bars(d.drawdown.filter((_, i, a) => i % Math.max(1, Math.floor(a.length / 18)) === 0))}</div></div>
      <div class="tile"><div class="tt">胜率</div><div class="tv num">${d.win_rate == null ? "—" : pct(d.win_rate, 0)}</div><div class="tu">${d.closed_trades ? `${d.closed_trades} 笔已平仓 · 累计已实现` : "尚无平仓，持仓离场后统计"}</div><div class="tc">${cum.length > 1 ? MiniCharts.line(cum) : ""}</div></div>
      <div class="tile donut"><div class="tt">敞口构成</div>
        <div class="tc">${MiniCharts.donut([{ v: longN, c: "#5ee0d6" }, { v: shortN, c: "#4b3aa6" }, { v: Math.max(0, cash), c: "#ece8fd" }])}</div>
        <div class="legend"><div><i style="background:#5ee0d6"></i>现货多 ${f2(longN, 0)}</div><div><i style="background:#4b3aa6"></i>永续空 ${f2(shortN, 0)}</div><div><i style="background:#ece8fd"></i>现金 ${f2(Math.max(0, cash), 0)}</div></div></div>
      <div class="tile"><div class="tt">自动交易</div><div class="tv"><span class="pill ${w.running ? "long" : "flat"}">${w.running ? "运行中" : "已停止"}</span></div>
        <div class="tu" style="margin-top:8px">${w.running ? `每 ${st.settings.worker.interval_sec} 秒一轮 · 下次约 ${w.next_run_in_sec ?? "—"} 秒后` : "可在风控页开启"}<br>上次 ${t(w.last_run)}</div>
        <button class="btn ghost sm tile-act" data-go="risk">风控与自动交易 →</button></div>
    </section>
    <div class="note foot">系统化纸面 / 研究工具，不构成投资建议；实盘交易可能亏损全部本金。数据来自 ${VN[v]} 官方公共行情 · 更新于 ${tFull(d.time)}。</div>
  </div>`;
  bindGo();
  document.querySelectorAll("#page .tx[data-sym]").forEach((el) => (el.onclick = () => goSignal(el.dataset.sym, el.dataset.mkt)));
}
function bindGo() { document.querySelectorAll("#page [data-go]").forEach((el) => (el.onclick = () => (location.hash = "#/" + el.dataset.go))); }

/* ---------- 信号 / 进出场 ---------- */
const IV_SEC = { "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400 };
async function pageSignals() {
  const s = S.status.settings.strategy;
  $("#page").innerHTML = `
    <div class="fit sig-page">
    <div class="panel chart-panel">
      <div class="chart-head">
        <div><h3 id="chartTitle">K 线与均线</h3><div class="note" id="chartSrc">加载中…</div></div>
        <div class="chart-ctl">
          <div class="seg" id="mktSeg" role="group" aria-label="市场"><button data-m="spot">现货</button><button data-m="perp">USDT 永续</button></div>
          <div class="seg" id="rangeSeg" role="group" aria-label="显示范围"><button data-r="7">1 周</button><button data-r="30">1 月</button><button data-r="all">全部</button></div>
        </div>
      </div>
      <div class="chart-box" id="candleChart"><div class="empty">加载中…</div></div>
      <div class="chart-legend"><span><i style="background:#2cc4c9"></i>快线 SMA${s.fast_ma}</span><span><i style="background:#6c5ce7"></i>慢线 SMA${s.slow_ma}</span><span>▲▼ 收盘确认的均线交叉</span><span class="muted">时间为北京时间 · 图表 TradingView Lightweight Charts™</span></div>
    </div>
    <div class="sec-title sig-title"><div><h3>当前信号与进出场建议</h3><div class="note">策略 ${esc(s.rule_id)}：${s.interval} 已收盘 K 线上 SMA${s.fast_ma} / SMA${s.slow_ma} 判断方向。做多用现货，做空用 USDT 永续（1 倍）。点击一行在上方图表查看，并打开进出场详情。</div></div></div>
    <div class="panel sig-panel"><div class="sig-list" id="sigList"><div class="empty">正在从 ${VN[S.status.settings.venue]} 公共行情计算信号…</div></div><div id="sigPager"></div></div>
    </div>`;
  document.querySelectorAll("#mktSeg [data-m]").forEach((b) => (b.onclick = () => { S.chartMkt = b.dataset.m; loadCandles(); }));
  document.querySelectorAll("#rangeSeg [data-r]").forEach((b) => (b.onclick = () => { S.chartRange = b.dataset.r; applyRange(); }));
  try { if (!S.signals) S.signals = await api("/api/signals"); } catch (e) { $("#sigList").innerHTML = `<div class="empty neg">信号计算失败：${esc(e.message)}</div>`; return; }
  renderRight();
  const rows = S.signals.rows;
  S.selSym = S.selSym && rows.some((r) => r.symbol === S.selSym) ? S.selSym : rows.find((r) => !r.error)?.symbol;
  const selRow = rows.find((r) => r.symbol === S.selSym);
  S.chartMkt = S.chartMkt || (selRow && selRow.signal_market) || "spot";
  renderSigGrid();
  loadCandles();
}
const STATE = { holding: ["持有中", "info"], entry_pending: ["待入场", "warn"], blocked: ["止损后观望", "flat"], trend_wait: ["逆趋势·暂缓", "flat"], short_paused: ["空头熔断·暂缓", "flat"], flat: ["空仓观望", "flat"] };
const sigCn = (x) => (x > 0 ? "做多" : x < 0 ? "做空" : "空仓");
function renderSigGrid() { renderSigList(); }
function sigPxKind(r) {
  return r.ref_price_kind === "mark" ? "永续标记价" : r.ref_price_kind === "last" ? "现货最新价" : "收盘价";
}
function renderSigList() {
  const g = $("#sigList"); if (!g || !S.signals) return;
  const head = `<div class="sig-head" aria-hidden="true"><span>币种</span><span>方向</span><span>标记价</span><span>建议仓位</span><span>止损价</span><span>状态</span></div>`;
  const stPg = pgState("signals", S.signals.rows.length, fitRows(g, 56, 34, 4));
  const rows = S.signals.rows.slice(stPg.start, stPg.end).map((r) => {
    if (r.error) return `<div class="sig-row err">${coin(r.symbol)}<div class="sig-sym"><div class="nm">${base(r.symbol)}</div><div class="note neg">${esc(r.error)}</div></div></div>`;
    const mkt = r.market === "-" ? "spot" : r.market;
    const px = pxOk(r.ref_price) ? fp(r.ref_price) : "—";
    const size = r.target_notional_usdt ? f2(r.target_notional_usdt, 0) + " U" : "—";
    const st = STATE[r.state] || ["—", "flat"];
    return `<button type="button" class="sig-row ${r.symbol === S.selSym ? "sel" : ""}" data-sym="${r.symbol}" aria-label="${base(r.symbol)} 信号，点击查看 K 线与详情">
      <span class="sig-sym">${coin(r.symbol)}<span><b>${base(r.symbol)}</b><small class="muted">/USDT</small></span></span>
      <span class="sig-dir"><span class="side-tag ${r.side}">${sideCn(r.side)}</span></span>
      <span class="numcol"><b class="num" data-px="${r.symbol}:${mkt}">${px}</b><small>${sigPxKind(r)}</small></span>
      <span class="numcol"><b class="num">${size}</b><small>${r.target_notional_usdt ? "占权益 " + pct(r.target_weight, 1) : "不开仓"}</small></span>
      <span class="numcol"><b class="num">${r.stop_price && pxOk(r.stop_price) ? fp(r.stop_price) : "—"}</b><small>${r.risk_usdt ? "最多亏 " + f2(r.risk_usdt) + " U" : "—"}</small></span>
      <span class="sig-st"><span class="pill ${st[1]}">${st[0]}</span></span>
    </button>`;
  }).join("");
  g.innerHTML = head + (rows || '<div class="empty">暂无信号</div>');
  g.querySelectorAll(".sig-row[data-sym]").forEach((el) => {
    el.onclick = () => { selectSignal(el.dataset.sym); showSignalModal(el.dataset.sym); };
  });
  const pg = $("#sigPager");
  if (pg) { pg.innerHTML = pagerHtml("signals", stPg); bindPager("signals", renderSigList); }
  tightenIfOverflow(g, "signals", renderSigList);
  if (S.sigModalSym && !$("#modal").classList.contains("hidden")) renderSignalModal($("#modalCard"), S.sigModalSym);
}
function selectSignal(sym) {
  S.selSym = sym;
  const rr = S.signals?.rows.find((x) => x.symbol === sym); if (rr && rr.signal_market && rr.signal_market !== "-") S.chartMkt = rr.signal_market;
  document.querySelectorAll(".sig-row[data-sym]").forEach((x) => x.classList.toggle("sel", x.dataset.sym === sym));
  loadCandles();
  const page = $("#page"); if (page && page.scrollTo) page.scrollTo({ top: 0, behavior: "smooth" });
}
function signalDetailBody(r) {
  if (r.error) return `<div class="note neg">${esc(r.symbol)}：${esc(r.error)}</div>`;
  const st = STATE[r.state] || ["—", "flat"];
  const mkt = r.market === "-" ? "spot" : r.market;
  return `<div class="kv">
      <div><small>建议仓位</small><b class="num">${r.target_notional_usdt ? f2(r.target_notional_usdt, 0) + " U" : "—"}</b><em>${r.target_notional_usdt ? "占权益 " + pct(r.target_weight, 1) : "不开仓"}</em></div>
      <div><small>止损价</small><b class="num">${r.stop_price && pxOk(r.stop_price) ? fp(r.stop_price) : "—"}</b><em>${r.risk_usdt ? "最多亏 " + f2(r.risk_usdt) + " U" : "—"}</em></div>
      <div><small>状态</small><b><span class="pill ${st[1]}">${st[0]}</span></b><em>${r.conflict ? "现货/永续冲突" : "&#160;"}</em></div>
    </div>
    <div class="tm">
      <p><i>入场</i><span>${esc(ptText(r.entry_timing))}</span></p>
      <p><i>离场</i><span>${esc(ptText(r.exit_timing))}</span></p>
      <p><i>均线</i><span>快线 ${fp(r.sma_fast)} / 慢线 ${fp(r.sma_slow)}</span></p>
      <p><i>分市场</i><span>现货 ${sigCn(r.spot_signal)} · 永续 ${sigCn(r.perp_signal)}${r.conflict ? " → 冲突时空仓" : ""}</span></p>
      <p><i>仓位上限</i><span>${({ risk: "5% 单笔风险", weight: "20% 单币权重", gross: "总敞口 1×", none: "—" })[r.capped_by]}</span></p>
      <p><i>时间</i><span>信号截至 ${t(r.as_of)} 收盘 · 下次检查 ${t(r.next_check)}</span></p>
      <p><i>数据</i><span class="src">${esc(r.data_source)} · ${esc(r.source_host)} · 拉取 ${t(r.fetched_at)}${r.warning ? ` · <span class="neg">${esc(r.warning)}</span>` : ""}</span></p>
      ${markCandleLine(r.symbol)}
    </div>`;
}
function renderSignalModal(root, sym) {
  if (!root || !S.signals) return;
  const r = S.signals.rows.find((x) => x.symbol === sym);
  if (!r) return;
  const mkt = r.market === "-" ? "spot" : r.market;
  const pxLabel = r.error ? "" : `${sigPxKind(r)} <b class="num" data-px="${r.symbol}:${mkt}">${pxOk(r.ref_price) ? fp(r.ref_price) : "—"}</b>`;
  root.innerHTML = `<div class="sig-modal-head">
      ${coin(r.symbol, "lg")}
      <div class="sig-modal-title"><h3>${base(r.symbol)}<span class="muted" style="font-weight:500">/USDT</span></h3>
        <div class="px">${pxLabel}${!r.error && r.market !== "-" ? " · " + r.market_cn : ""}</div></div>
      ${r.error ? "" : `<span class="badge lg ${r.side}">${sideCn(r.side)}</span>`}
      <button type="button" class="sig-modal-close" data-close aria-label="关闭">${ic("x") || ""}</button>
    </div>
    <div class="sig-modal-body">${signalDetailBody(r)}</div>`;
  const closeBtn = root.querySelector("[data-close]");
  if (closeBtn) {
    if (!closeBtn.innerHTML.trim()) closeBtn.textContent = "×";
    closeBtn.onclick = closeModal;
  }
}
function showSignalModal(sym) {
  const r = S.signals?.rows.find((x) => x.symbol === sym);
  if (!r || r.error) return;
  S.sigModalSym = sym;
  const card = $("#modalCard");
  card.classList.add("sig-detail");
  $("#modal").classList.remove("hidden");
  renderSignalModal(card, sym);
  const f = card.querySelector("[data-close]");
  f && f.focus();
}

async function loadCandles() {
  const el = $("#candleChart"); if (!el || !S.selSym) return;
  const m = S.chartMkt || "spot", iv = S.status.settings.strategy.interval;
  document.querySelectorAll("#mktSeg [data-m]").forEach((b) => b.classList.toggle("on", b.dataset.m === m));
  $("#chartTitle").textContent = `${base(S.selSym)}/USDT · ${m === "perp" ? "USDT 永续" : "现货"} · ${iv} K 线`;
  const req = (S._candleReq = (S._candleReq || 0) + 1);
  try {
    const d = await api(`/api/candles?symbol=${S.selSym}&bars=300&market=${m}`);
    if (req !== S._candleReq || !document.body.contains(el)) return;
    S.chart = BigCharts.candles(el, d); S.chart._sym = S.selSym; S.chart._mkt = m; S.chart._iv = IV_SEC[iv] || 14400; S.chart._src = `${d.data_source} · ${d.source_host}`; S.chart._n = d.candles.length;
    S.chart._loadedAt = Date.now();
    applyRange(); applyForming(); renderChartSrc();
  } catch (e) { el.innerHTML = `<div class="empty neg">${esc(e.message)}</div>`; }
}
function applyRange() {
  const c = S.chart, r = S.chartRange || "30";
  document.querySelectorAll("#rangeSeg [data-r]").forEach((b) => b.classList.toggle("on", b.dataset.r === r));
  if (!c || !c._n) return;
  if (r === "all") { c.timeScale().fitContent(); return; }
  const bars = Math.round((+r * 86400) / c._iv);
  c.timeScale().setVisibleLogicalRange({ from: Math.max(0, c._n - bars), to: c._n + 2 });
}
function renderChartSrc() {
  const c = S.chart, el = $("#chartSrc"); if (!c || !el) return;
  const live = c._liveAt ? `实时更新于 ${PT.clock(new Date(c._liveAt))}:${String(new Date(c._liveAt).getSeconds()).padStart(2, "0")} 北京时间（${c._liveKind}）` : "等待实时推送…";
  el.innerHTML = `<span class="live-dot ${c._liveAt && Date.now() - c._liveAt < 30000 ? "on" : ""}"></span>${live} · ${c._n} 根已收盘 K 线来自 ${esc(c._src)}`;
}

/* ---------- 回测 ---------- */
async function pageBacktest() {
  const s = S.status.settings;
  $("#page").innerHTML = `
  <div class="fit bt-page">
  <div class="panel bt-params"><div class="sec-title"><h3>回测参数</h3><span class="note">使用交易所真实公共历史 K 线 · 第 t 根收盘信号在第 t+1 根开盘成交（无前视）</span></div>
    <div class="bt-form">
      <label class="field">交易所<select id="btVenue"><option value="okx">OKX</option><option value="gate">Gate.io</option></select></label>
      <label class="field">K 线根数 (${s.strategy.interval})<input id="btBars" type="number" value="1500" min="200" max="5000"/></label>
      <label class="field">快线 SMA<input id="btFast" type="number" value="${s.strategy.fast_ma}"/></label>
      <label class="field">慢线 SMA<input id="btSlow" type="number" value="${s.strategy.slow_ma}"/></label>
      <label class="field">ATR 止损倍数<input id="btAtr" type="number" step="0.5" value="${s.strategy.atr_stop_mult}"/></label>
      <button class="btn" id="btRun" style="height:42px">${ic("play")}运行回测</button>
    </div></div>
  <div id="btOut" class="bt-out">${S.bt?.summary ? "" : '<div class="empty">设置参数后点击“运行回测”。默认标的池 8 个主流币，首次拉取历史数据约需 20–40 秒。</div>'}</div></div>`;
  $("#btVenue").value = s.venue;
  $("#btRun").onclick = runBacktest;
  if (S.bt?.summary) renderBt();
  else { try { const l = await api("/api/backtest/latest"); if (l.summary) { S.bt = l; renderBt(); } } catch (_) {} }
}
async function runBacktest() {
  const b = $("#btRun"); b.disabled = true; b.innerHTML = '<span class="spin"></span> 回测中…';
  try {
    S.bt = await api("/api/backtest", { method: "POST", body: { venue: $("#btVenue").value, bars: +$("#btBars").value, fast_ma: +$("#btFast").value, slow_ma: +$("#btSlow").value, atr_stop_mult: +$("#btAtr").value } });
    renderBt(); toast("回测完成");
  } catch (e) { toast("回测失败：" + e.message, true); }
  finally { b.disabled = false; b.innerHTML = ic("play") + "运行回测"; }
}
function renderBt() {
  const r = S.bt, m = r.summary;
  const M = (k, v, c = "", f = false) => `<div class="metric ${f ? "feature" : ""}"><small>${k}</small><b class="num ${c}">${v}</b></div>`;
    $("#btOut").innerHTML = `
  <div class="metrics">
    ${M("总收益", pct(m.total_return), "", true)}${M("期末权益 (USDT)", f2(m.ending_equity_usdt))}${M("最大回撤", pct(m.max_drawdown), "neg")}${M("夏普比率（年化）", m.sharpe == null ? "—" : m.sharpe.toFixed(2))}
    ${M("胜率", pct(m.win_rate, 1))}${M("盈亏比", m.profit_factor == null ? "—" : m.profit_factor.toFixed(2))}${M("已平 / 持仓中", `${m.closed_trades} / ${m.open_trades}`)}${M(esc(m.benchmark), pct(m.benchmark_return), cls(m.benchmark_return))}
  </div>
  <div class="panel bt-chart-panel"><div class="sec-title" style="margin:4px 8px 8px"><h3>权益曲线与回撤</h3><span class="note">#${m.run_id ?? ""} ${esc((m.venue || "").toUpperCase())} · ${esc(m.interval)} · ${tFull(m.start_time)} → ${tFull(m.end_time)} · ${m.bars} 根 · 手续费 ${m.fee_bps} bps · 止损离场 ${m.stop_exits} 次</span></div><div class="chart-box" id="eqChart"></div></div>
  <div class="panel bt-trades-panel">
    <div class="sec-title"><h3>回测成交（${r.trades.length}）</h3><div id="btPager"></div></div>
    <div id="btTrades" class="tbl-wrap"></div>
    <div class="note" title="数据：${esc(m.data_source)} · ${esc(m.source_host)} · 拉取 ${tFull(m.fetched_at)}">官方公共历史 K 线（做多=现货，做空=USDT 永续）；未计资金费率与滑点；不代表未来收益。生成于 ${tFull(r.generated_at)}。</div>
  </div>`;
  BigCharts.equity($("#eqChart"), r.equity);
  renderBtTrades();
}

/* ---------- 持仓 ---------- */
function pagePositions() {
  const d = S.dash;
  $("#page").innerHTML = `<div class="fit pos-page">
  <div class="metrics"><div class="metric feature"><small>纸面权益</small><b class="num">${f2(d.equity)}</b></div><div class="metric"><small>可用现金</small><b class="num">${f2(d.cash_free)}</b></div><div class="metric"><small>总敞口 / 净敞口</small><b class="num">${f2(d.gross, 0)} / ${sgn(d.net, 0)}</b></div><div class="metric"><small>未实现盈亏</small><b class="num ${cls(d.unrealized)}">${sgn(d.unrealized)}</b></div></div>
  <div class="panel pos-panel"><div class="sec-title"><h3>当前纸面持仓（${d.positions.length}）</h3></div>
  <div id="posTable"></div>
  <div id="posPager"></div>
  <div class="note">纸面账本持久化保存在 data/qtw.sqlite（重启不丢失；CSV 仅为导出）。永续空头按 1 倍保证金计，占用等额现金。</div></div></div>`;
  renderPosTable();
}
function renderPosTable() {
  const host = $("#posTable"), d = S.dash; if (!host || !d) return;
  if (!d.positions.length) { host.innerHTML = '<div class="empty">当前空仓。开启自动交易或点击右上角「跑一轮」执行一次系统化周期。</div>'; const pg = $("#posPager"); if (pg) pg.innerHTML = ""; return; }
  const st = pgState("positions", d.positions.length, fitRows(host, 56, 36, 4));
  const slice = d.positions.slice(st.start, st.end);
  host.innerHTML = `<div class="tbl-wrap"><table class="tbl pos-tbl"><thead><tr><th>标的</th><th>方向</th><th class="col-venue">行情源</th><th>数量</th><th>入场价</th><th class="col-etime">入场时间</th><th>最新价</th><th>止损价</th><th class="col-notional">名义</th><th>权重</th><th>未实现</th></tr></thead><tbody>
  ${slice.map((p) => {
    const mark = posMark(p), pnl = posUpnl(p, mark);
    const live = `data-sym="${p.symbol}" data-mkt="${p.market}" data-entry="${p.entry_price}" data-qty="${p.qty}" data-side="${p.side}" data-mark="${p.mark_price ?? ""}" data-mark-time="${esc(p.mark_time || "")}"`;
    return `<tr><td><div style="display:flex;gap:10px;align-items:center">${coin(p.symbol)}<b>${p.symbol}</b></div></td><td><span class="pill ${p.side}">${sideCn(p.side)} · ${mktCn(p.market)}</span></td><td class="col-venue">${esc((p.venue || S.status.settings.venue || "—").toUpperCase())}</td><td class="num">${fp(p.qty)}</td><td class="num">${fpPx(p.entry_price)}</td><td class="col-etime">${tFull(p.entry_time)}</td><td class="num"><span data-live="px" ${live}>${fpPx(mark)}</span><br><small class="muted">${esc(p.mark_source || "—")}</small></td><td class="num">${fp(p.stop_price)}${stopRisk(p)}</td><td class="num col-notional">${mark != null ? f2(p.qty * mark) : "—"}</td><td class="num"><span data-live="weight" ${live}>${pct(p.weight, 1)}</span></td><td class="num ${cls(pnl.usdt)}" data-live="pnl" data-stacked="1" ${live}><span data-live-pnl-txt>${fmtPnl(pnl, true)}</span></td></tr>`;
  }).join("")}</tbody></table></div>`;
  const pg = $("#posPager"); if (pg) { pg.innerHTML = pagerHtml("positions", st); bindPager("positions", renderPosTable); }
  tightenIfOverflow(host, "positions", renderPosTable);
}

/* ---------- 成交 ---------- */
async function pageTrades() {
  $("#page").innerHTML = '<div class="empty">加载中…</div>';
  try {
    S.trades = await api("/api/trades");
    S.orders = await api("/api/orders");
  } catch (e) { $("#page").innerHTML = `<div class="empty neg">${esc(e.message)}</div>`; return; }
  renderTradesPage(true);
}
function renderTradesPage(rebuild) {
  const rows = S.trades || [];
  const orders = S.orders || [];
  const route = orders.filter((o) => o.status && o.status !== "paper_filled");
  if (rebuild !== false || !$("#tradeTable")) {
    $("#page").innerHTML = `<div class="fit trades-page">
      <div class="panel trades-panel">
        <div class="sec-title"><h3>纸面成交（${rows.length}）</h3></div>
        <div id="tradeTable"></div>
        <div id="tradePager"></div>
      </div>
      ${route.length ? `<details class="panel route-log"><summary>路由日志（${route.length} 条未成交 / 拦截记录）</summary>
        <div class="tbl-wrap route-wrap"><table class="tbl"><thead><tr><th>时间</th><th>模式</th><th>交易所</th><th>标的</th><th>动作</th><th>数量</th><th>参考价</th><th>状态</th><th>说明</th></tr></thead><tbody>
        ${route.map((o) => `<tr><td>${tFull(o.time)}</td><td>${o.mode === "live" ? '<span class="pill short">实盘</span>' : '<span class="pill info">纸面</span>'}</td><td>${esc((o.venue || "").toUpperCase())}</td><td>${esc(o.symbol)}</td><td>${esc(o.action)}</td><td class="num">${fp(+o.qty)}</td><td class="num">${fpPx(+o.ref_price)}</td><td>${esc(o.status)}</td><td class="reason">${esc(o.detail)}</td></tr>`).join("")}
        </tbody></table></div></details>` : ""}
    </div>`;
  }
  const host = $("#tradeTable"); if (!host) return;
  if (!rows.length) { host.innerHTML = '<div class="empty">暂无成交</div>'; const pg = $("#tradePager"); if (pg) pg.innerHTML = ""; return; }
  const st = pgState("trades", rows.length, fitRows(host, 100, 52, 3));
  const slice = rows.slice(st.start, st.end);
  host.innerHTML = `<div class="tbl-wrap"><table class="tbl trades-tbl"><colgroup>
    <col class="c-time"/><col class="c-sym"/><col class="c-qty"/><col class="c-px"/><col class="c-px"/><col class="c-id"/><col class="c-fee"/><col class="c-pnl"/>
  </colgroup><thead><tr><th>时间</th><th>标的 / 原因</th><th>数量</th><th>进场价</th><th>出场价</th><th>单号</th><th>手续费</th><th>盈亏</th></tr></thead><tbody>
  ${slice.map((tr) => tradeRowHtml(tr)).join("")}</tbody></table></div>`;
  const pg = $("#tradePager"); if (pg) { pg.innerHTML = pagerHtml("trades", st); bindPager("trades", () => renderTradesPage(false)); }
  tightenIfOverflow(host, "trades", () => renderTradesPage(false));
}
function tradeRowHtml(tr) {
  const open = tr.status === "open";
  const mark = open ? currentPx(tr.symbol, tr.market, tr.mark_price, tr.mark_time) : null;
  let pnl = { usdt: tr.pnl_usdt, pct: tr.pnl_pct };
  if (open) pnl = posUpnl({ entry_price: tr.entry_price, qty: tr.qty, side: tr.side }, mark);
  // open: show price pnl net of known fees when we have a live/book price
  if (open && pnl.usdt != null) { pnl = { usdt: pnl.usdt - Number(tr.fee_usdt || 0), pct: (tr.entry_price && tr.qty) ? (pnl.usdt - Number(tr.fee_usdt || 0)) / (Number(tr.entry_price) * Number(tr.qty)) : null }; }
  const live = open ? `data-sym="${tr.symbol}" data-mkt="${tr.market}" data-entry="${tr.entry_price}" data-qty="${tr.qty}" data-side="${tr.side}" data-mark="${tr.mark_price ?? ""}" data-mark-time="${esc(tr.mark_time || "")}"` : "";
  const reason = [tr.entry_reason ? "入场：" + ptText(tr.entry_reason) : "", tr.exit_reason ? "离场：" + ptText(tr.exit_reason) : ""].filter(Boolean).join("  ");
  const mode = (tr.mode === "live" ? "实盘" : "纸面") + (tr.venue ? " · " + String(tr.venue).toUpperCase() : "");
  const exitCell = open
    ? `<span class="exit-dash">—</span><span class="exit-live" data-live="px" data-px-prefix="现价 " ${live}>${pxOk(mark) ? "现价 " + fpPx(mark) : "—"}</span>`
    : fpPx(tr.exit_price);
  return `<tr class="${open ? "open-tr" : ""}">
    <td class="time-c"><div>${tr.entry_time ? tCompact(tr.entry_time) : "—"}</div><div class="ds">${open ? "持仓中" : (tr.exit_time ? tCompact(tr.exit_time) : "—")}</div></td>
    <td class="sym-c"><div class="sym-line">${coin(tr.symbol)}<div><b>${base(tr.symbol)}</b><div class="ds"><span class="side-tag ${tr.side}">${sideCn(tr.side)}</span> ${mktCn(tr.market)} · ${esc(mode)}</div></div></div>
      ${reason ? `<div class="reason" title="${esc(reason)}">${esc(reason)}</div>` : ""}</td>
    <td class="num">${fqty(tr.qty)}</td>
    <td class="num">${fpPx(tr.entry_price)}</td>
    <td class="num exit-cell">${exitCell}</td>
    <td class="num">${tr.trade_id ?? "—"}</td>
    <td class="num">${f2(tr.fee_usdt, 4)}</td>
    <td class="num pnl-cell ${cls(pnl.usdt)}" ${open ? `data-live="pnl" data-stacked="1" data-fee="${tr.fee_usdt || 0}" ${live}` : ""}><span data-live-pnl-txt>${fmtPnl(pnl, true)}</span></td>
  </tr>`;
}

/* ---------- 风控 / 自动交易 ---------- */
function pageRisk() {
  const s = S.status.settings, w = S.status.worker;
  $("#page").innerHTML = `
  <div class="fit set-page" id="riskPage">
    <nav class="set-nav" role="tablist" aria-label="风控分类">
      <button type="button" role="tab" data-tab="auto">${ic("play")}自动交易</button>
      <button type="button" role="tab" data-tab="kill">${ic("alert")}紧急操作</button>
      <button type="button" role="tab" data-tab="rules">${ic("risk")}风控规则</button>
      <button type="button" role="tab" data-tab="strategy">${ic("settings")}策略参数</button>
      <button type="button" role="tab" data-tab="universe">${ic("trades")}标的池</button>
    </nav>
    <div class="set-main">
      <div class="set-panes">
        <section class="set-pane panel" data-pane="auto" role="tabpanel">
          <div class="sec-title"><h3>自动交易 <span class="muted" style="font-weight:500;font-size:13px">纸面执行</span>${infoTip("<b>后台循环每隔设定秒数：</b><ol><li>拉取 OKX / Gate 官方公共行情</li><li>用已收盘 K 线计算信号</li><li>检查止损</li><li>在<b>纸面账本</b>按最新价调仓</li></ol>实盘只有在「设置」页通过全部闸门后才会发单。", "自动交易说明")}</h3>
            <span class="pill ${w.running ? "long" : "flat"}">${w.running ? "运行中" : "已停止"}</span></div>
          <div class="worker-row">
            <label class="field" style="width:150px">检查间隔（秒）<input id="wInt" type="number" min="60" value="${s.worker.interval_sec}"/></label>
            <button class="btn ${w.running ? "stop" : "go"}" id="wToggle" aria-pressed="${w.running}">${w.running ? ic("stop") + "停止自动交易" : ic("play") + "开启自动交易"}</button>
            <button class="btn ghost" id="cycleNow" title="手动跑一轮系统化周期（纸面）">${ic("play")}跑一轮</button>
          </div>
          <div class="note" style="margin-top:12px">上次执行：${tFull(w.last_run, true)}${w.running ? ` · 下次约 ${w.next_run_in_sec ?? "—"} 秒后` : ""}${w.last_error ? `<br><span class="neg">错误：${esc(w.last_error)}</span>` : ""}</div>
        </section>
        <section class="set-pane panel danger-panel" data-pane="kill" role="tabpanel">
          <div class="sec-title"><h3>紧急操作</h3></div>
          <div class="danger-acts">
            <div class="da"><button class="btn danger" id="killBig">${ic("stop")}紧急停止</button>${infoTip("<b>紧急停止（Kill Switch）</b><ul><li>停止后台自动交易</li><li>关闭实盘开关，切回纸面</li><li>按最新公共价<b>平掉全部纸面持仓</b></li></ul>不会向交易所发送任何订单。点击后还会再确认一次。", "紧急停止说明")}</div>
            <div class="da"><button class="btn ghost danger-ghost" id="resetPaper">重置纸面账本</button>${infoTip("<b>重置纸面账本</b><ul><li>清空全部纸面持仓、成交与账本历史</li><li>恢复起始资金（当前 " + f2(s.risk.starting_equity_usdt, 0) + " USDT）</li><li>需先停止自动交易</li></ul>点击后还会再确认一次。", "重置说明")}</div>
          </div>
        </section>
        <section class="set-pane panel" data-pane="rules" role="tabpanel">
          <div class="sec-title"><h3>风控规则</h3><span class="note">上限只能调低，不能调高</span></div>
          <div class="grid form4">
            <label class="field">起始纸面资金 (USDT)<input id="rEq" type="number" value="${s.risk.starting_equity_usdt}"/><span class="hint">重置账本后生效</span></label>
            <label class="field">单笔最大风险<input id="rRisk" type="number" step="0.005" max="0.05" value="${s.risk.max_risk_per_trade}"/><span class="hint">≤ 0.05（5%）；止损较近时单币上限先生效，实际单笔风险≈单币上限×止损距离</span></label>
            <label class="field">单币最大权重<input id="rW" type="number" step="0.01" max="0.2" value="${s.risk.max_weight_per_name}"/><span class="hint">≤ 0.20（20%）</span></label>
            <label class="field">手续费假设 (bps)<input id="rFee" type="number" step="0.5" value="${s.fees.taker_bps}"/><span class="hint">默认 taker 4 bps</span></label>
          </div>
          <div style="display:flex;gap:28px;margin-top:16px;flex-wrap:wrap;align-items:center">
            <label class="toggle"><input type="checkbox" id="rSpot" ${s.risk.allow_spot_long ? "checked" : ""}/><span class="tr"></span>允许现货做多</label>
            <label class="toggle"><input type="checkbox" id="rPerp" ${s.risk.allow_perp_short ? "checked" : ""}/><span class="tr"></span>允许永续做空</label>
            <span class="note">固定：永续 1 倍杠杆 · 总敞口 ≤ 1× 权益</span>
          </div>
        </section>
        <section class="set-pane panel" data-pane="strategy" role="tabpanel">
          <div class="sec-title"><h3>策略参数 · ${esc(s.strategy.rule_id)}</h3></div>
          <div class="grid form4">
            <label class="field">K 线周期<select id="sInt">${["15m", "1h", "4h", "1d"].map((x) => `<option ${x === s.strategy.interval ? "selected" : ""}>${x}</option>`).join("")}</select></label>
            <label class="field">快线 SMA<input id="sFast" type="number" value="${s.strategy.fast_ma}"/></label>
            <label class="field">慢线 SMA<input id="sSlow" type="number" value="${s.strategy.slow_ma}"/></label>
            <label class="field">ATR 周期<input id="sAtrP" type="number" value="${s.strategy.atr_period}"/></label>
            <label class="field">ATR 止损倍数<input id="sAtr" type="number" step="0.5" value="${s.strategy.atr_stop_mult}"/></label>
            <label class="field" title="交叉后方向需连续保持几根已收盘 K 线才入场">信号确认根数<input id="sConf" type="number" min="1" max="5" step="1" value="${s.strategy.confirm_bars ?? 1}"/></label>
            <label class="field" title="只拦截逆势新开仓：做多需收盘价在该 SMA 之上，做空需在其下；不会因此平掉已有持仓。填 0 关闭">趋势过滤 SMA（0=关闭）<input id="sTrend" type="number" min="0" max="400" step="10" value="${s.strategy.trend_ma ?? 0}"/></label>
            <label class="field" title="用同一规则跑一本只做空的影子账本：最近 N 根 K 线已平仓影子空单合计亏损时，暂停新开空单；转正后自动恢复。不会平掉已有持仓。填 0 关闭">空头熔断回看根数（0=关闭）<input id="sSB" type="number" min="0" max="500" step="10" value="${s.strategy.short_breaker_bars ?? 0}"/></label>
            <label class="field" title="仅回测生效（模拟盘 / 实盘暂不加仓）：持仓前一根收盘浮盈 ≥ k × R（R = 入场价到止损的距离）时，下一根开盘加仓一次，止损不动。填 0 关闭">浮盈加仓触发 R（0=关闭·仅回测）<input id="sPyrR" type="number" min="0" max="5" step="0.25" value="${s.strategy.pyramid_r ?? 0}"/></label>
            <label class="field" title="加仓名义 = 比例 × 原名义，同时受单币权重上限与总敞口上限约束">加仓比例（× 原名义）<input id="sPyrF" type="number" min="0" max="1" step="0.25" value="${s.strategy.pyramid_frac ?? 0.5}"/></label>
          </div>
        </section>
        <section class="set-pane panel" data-pane="universe" role="tabpanel">
          <div class="sec-title"><h3>标的池（USDT 交易对）</h3></div>
          <div class="chips" id="chips"></div>
          <div style="display:flex;gap:10px;margin-top:14px"><input id="addSym" class="r-search" style="margin:0;width:220px" placeholder="例如 LINK 或 LINKUSDT" aria-label="添加交易对"/><button class="btn ghost sm" id="addSymBtn">添加</button></div>
        </section>
      </div>
      <div class="savebar" id="saveBar"><span class="note" id="saveHint">修改参数后，点「保存设置」才会生效。</span><button class="btn" id="saveRisk">保存设置</button></div>
    </div>
  </div>`;
  bindTabs("riskTab", "#riskPage", S.riskTab || "auto");
  let syms = [...s.symbols];
  const dirty = () => { $("#saveBar").classList.add("dirty"); $("#saveHint").textContent = "有未保存的修改"; };
  const chips = () => { $("#chips").innerHTML = syms.map((x) => `<span class="c">${coin(x)}${x}<button data-rm="${x}" title="移除 ${x}" aria-label="移除 ${x}">×</button></span>`).join(""); document.querySelectorAll("[data-rm]").forEach((b) => (b.onclick = () => { syms = syms.filter((x) => x !== b.dataset.rm); chips(); dirty(); })); };
  chips();
  document.querySelectorAll("#page .set-pane input:not(#addSym), #page .set-pane select").forEach((i) => i.addEventListener("input", dirty));
  const add = () => { let v = $("#addSym").value.trim().toUpperCase().replace(/[-_/]/g, ""); if (!v) return; if (!v.endsWith("USDT")) v += "USDT"; if (!syms.includes(v)) { syms.push(v); dirty(); } $("#addSym").value = ""; chips(); };
  $("#addSymBtn").onclick = add; $("#addSym").onkeydown = (e) => { if (e.key === "Enter") add(); };
  $("#saveRisk").onclick = async () => {
    const b = $("#saveRisk"); b.disabled = true;
    try {
      await api("/api/settings", { method: "PUT", body: { symbols: syms, worker: { interval_sec: +$("#wInt").value },
        risk: { starting_equity_usdt: +$("#rEq").value, max_risk_per_trade: +$("#rRisk").value, max_weight_per_name: +$("#rW").value, allow_spot_long: $("#rSpot").checked, allow_perp_short: $("#rPerp").checked },
        fees: { taker_bps: +$("#rFee").value },
        strategy: { interval: $("#sInt").value, fast_ma: +$("#sFast").value, slow_ma: +$("#sSlow").value, atr_period: +$("#sAtrP").value, atr_stop_mult: +$("#sAtr").value, confirm_bars: +$("#sConf").value, trend_ma: +$("#sTrend").value, short_breaker_bars: +$("#sSB").value, pyramid_r: +$("#sPyrR").value, pyramid_frac: +$("#sPyrF").value } } });
      toast("设置已保存"); S.signals = null; await refreshAll(); pageRisk();
    } catch (e) { toast("保存失败：" + e.message, true); b.disabled = false; }
  };
  $("#wToggle").onclick = async (e) => {
    const b = e.currentTarget; b.disabled = true;
    try {
      if (S.status.worker.running) { await api("/api/worker/stop", { method: "POST" }); toast("自动交易已停止"); }
      else { await api("/api/settings", { method: "PUT", body: { worker: { interval_sec: +$("#wInt").value } } }); await api("/api/worker/start", { method: "POST" }); toast("自动交易已开启（纸面执行）"); }
      await refreshAll(); pageRisk();
    } catch (er) { toast(er.message, true); b.disabled = false; }
  };
  $("#cycleNow").onclick = (e) => runCycle(e.currentTarget);
  $("#killBig").onclick = killSwitch;
  $("#resetPaper").onclick = async () => { if (!(await confirmBox("重置纸面账本", "将清空全部纸面持仓、成交与账本历史，并恢复起始资金。", "确认重置", true))) return; try { await api("/api/paper/reset", { method: "POST" }); toast("纸面账本已重置"); refreshAll(); } catch (e) { toast(e.message, true); } };
}

/* ---------- API / 设置 ---------- */
const KEYWAVE = `<svg class="deco" viewBox="0 0 400 170" preserveAspectRatio="none"><path d="M0 0H400V50C340 90 300 20 240 50S140 150 60 110 0 90 0 90Z" fill="#5ee0d6" opacity=".85"/></svg>`;
function pageSettings() {
  const st = S.status, s = st.settings, v = st.vault, live = st.mode === "live";
  const kc = (ex, name) => `<div class="keycard">${KEYWAVE}<h4>${name}</h4><div class="st">${v[ex].configured ? "已加密保存（AES / Fernet）" : "未配置 · 不影响行情、回测与纸面交易"}</div>
     <div class="masked">${v[ex].configured ? esc(v[ex].api_key_masked) : "•••• •••• •••• ••••"}</div><div class="st">Secret ${v[ex].secret_set ? "已保存（不可回显）" : "未保存"}${ex === "okx" ? ` · Passphrase ${v.okx.passphrase_set ? "已保存" : "未保存"}` : ""}</div></div>`;
  $("#page").innerHTML = `
  <div class="fit set-page" id="settingsPage">
    <nav class="set-nav" role="tablist" aria-label="设置分类">
      <button type="button" role="tab" data-tab="venue">${ic("signals")}行情源</button>
      <button type="button" role="tab" data-tab="okx">${ic("key")}OKX 密钥</button>
      <button type="button" role="tab" data-tab="gate">${ic("key")}Gate 密钥</button>
      <button type="button" role="tab" data-tab="live">${ic("alert")}实盘开关</button>
    </nav>
    <div class="set-main">
      <div class="set-panes">
        <section class="set-pane panel" data-pane="venue" role="tabpanel">
          <div class="sec-title"><h3>行情源</h3></div>
          <div class="venue-row"><div class="venue big" role="group" aria-label="行情源">${["okx", "gate"].map((x) => `<button type="button" data-v2="${x}" class="${s.venue === x ? "on" : ""}" ${(live || ((S.dash?.positions?.length || 0) && x !== s.venue)) ? "disabled" : ""}>${VN[x]}</button>`).join("")}</div>
          <div class="note">信号、K 线和纸面账本的计价都来自这里选择的交易所官方<b>公共</b>行情，不需要 API Key，切换后仍是纸面模式。${live ? '<br><span class="neg">实盘开启时不能切换，请先到「实盘开关」关闭实盘。</span>' : (S.dash?.positions?.length ? `<br><span class="neg">当前有 ${S.dash.positions.length} 个纸面持仓：请先平仓或重置后再切换行情源，避免入场/止损跨所混价。</span>` : "有纸面持仓时不能切换；只有在「实盘开关」通过全部闸门后，才会用它下真实单。")}</div></div>
        </section>
        <section class="set-pane panel" data-pane="okx" role="tabpanel">
          ${kc("okx", "OKX API 密钥")}
          <div class="grid" style="margin-top:16px">
            <label class="field">API Key<input id="okKey" autocomplete="off" placeholder="${v.okx.configured ? "留空 = 保持不变" : "粘贴 API Key"}"/></label>
            <label class="field">Secret Key<input id="okSec" type="password" autocomplete="new-password" placeholder="${v.okx.secret_set ? "留空 = 保持不变" : "粘贴 Secret"}"/></label>
            <label class="field">Passphrase<input id="okPass" type="password" autocomplete="new-password" placeholder="${v.okx.passphrase_set ? "留空 = 保持不变" : "创建 API 时设置的口令"}"/></label>
            <label class="toggle"><input type="checkbox" id="okDemo" ${s.live.okx_demo ? "checked" : ""}/><span class="tr"></span>使用 OKX 模拟盘环境</label>
            <div class="form-acts"><button class="btn" data-save="okx">${ic("key")}加密保存</button><button class="btn ghost" data-test="okx">只读连接测试</button><button class="btn ghost danger-ghost" data-del="okx">删除密钥</button></div>
          </div>
          <div class="note" style="margin-top:12px">密钥以 Fernet（AES-128 + HMAC）加密保存在 <b>data/secrets.enc</b>；主密钥来源：<b>${st.vault.key_source === "passphrase" ? "环境变量 QTW_MASTER_PASSPHRASE（scrypt 派生，不落盘）" : "本地密钥文件 data/vault.key（权限 600）"}</b>。密钥不写入数据库、CSV 或日志，页面只显示掩码。${st.vault.error ? `<br><span class="neg">${esc(st.vault.error)}</span>` : ""}</div>
        </section>
        <section class="set-pane panel" data-pane="gate" role="tabpanel">
          ${kc("gate", "Gate.io API 密钥")}
          <div class="grid" style="margin-top:16px">
            <label class="field">API Key<input id="gtKey" autocomplete="off" placeholder="${v.gate.configured ? "留空 = 保持不变" : "粘贴 API Key"}"/></label>
            <label class="field">Secret Key<input id="gtSec" type="password" autocomplete="new-password" placeholder="${v.gate.secret_set ? "留空 = 保持不变" : "粘贴 Secret"}"/></label>
            <label class="toggle"><input type="checkbox" id="gtTest" ${s.live.gate_testnet ? "checked" : ""}/><span class="tr"></span>使用 Gate 合约测试网（现货无测试网）</label>
            <div class="note">建议创建 API 时只勾选“交易 + 读取”，<b>不要开启提现权限</b>，并绑定 IP 白名单。</div>
            <div class="form-acts"><button class="btn" data-save="gate">${ic("key")}加密保存</button><button class="btn ghost" data-test="gate">只读连接测试</button><button class="btn ghost danger-ghost" data-del="gate">删除密钥</button></div>
          </div>
        </section>
        <section class="set-pane" data-pane="live" role="tabpanel">
          <div class="live-box">
            <h4>⚠️ 实盘交易开关（默认关闭）</h4>
            <div class="note" style="color:#7b3141">实盘交易可能亏损全部资金。本工具是系统化研究 / 纸面工具，不构成投资建议。开启需同时满足：模式=实盘、开关打开、输入确认语、启动时设置 <b>QTW_ALLOW_LIVE_ORDERS=1</b>、对应交易所密钥完整。任何一项不满足，订单只会被记录为“blocked”。</div>
            <div style="display:flex;gap:14px;align-items:end;margin-top:14px;flex-wrap:wrap">
              <label class="field" style="flex:1;min-width:280px">确认语（请完整输入：${esc(st.confirm_phrase_required)}）<input id="livePhrase" autocomplete="off" placeholder="${esc(st.confirm_phrase_required)}"/></label>
              ${st.settings.live.live_enabled ? '<button class="btn" id="liveOff">关闭实盘，回到纸面</button>' : '<button class="btn danger" id="liveOn">开启实盘模式</button>'}
            </div>
            <ul class="reasons">${st.live_block_reasons.length ? st.live_block_reasons.map((r) => `<li>${esc(r)}</li>`).join("") : "<li><b>全部闸门已通过：订单会真实发送！</b></li>"}</ul>
          </div>
        </section>
      </div>
    </div>
  </div>`;
  bindTabs("settingsTab", "#settingsPage", S.settingsTab || "venue");
  document.querySelectorAll("[data-v2]").forEach((b) => (b.onclick = () => setVenue(b.dataset.v2)));
  document.querySelectorAll("[data-save]").forEach((b) => (b.onclick = async () => {
    const ex = b.dataset.save;
    const body = ex === "okx" ? { api_key: $("#okKey").value, secret: $("#okSec").value, passphrase: $("#okPass").value } : { api_key: $("#gtKey").value, secret: $("#gtSec").value };
    try {
      await api(`/api/keys/${ex}`, { method: "PUT", body });
      await api("/api/live", { method: "PUT", body: { okx_demo: $("#okDemo").checked, gate_testnet: $("#gtTest").checked, confirm_phrase: S.status.settings.live.confirm_phrase } });
      toast("已加密保存（页面不会回显完整密钥）"); await refreshStatus(); pageSettings();
    } catch (e) { toast(e.message, true); }
  }));
  document.querySelectorAll("[data-del]").forEach((b) => (b.onclick = async () => { if (!(await confirmBox("删除密钥", `删除本地保存的 ${VN[b.dataset.del]} 密钥？`, "删除", true))) return; await api(`/api/keys/${b.dataset.del}`, { method: "DELETE" }); toast("已删除"); await refreshStatus(); pageSettings(); }));
  document.querySelectorAll("[data-test]").forEach((b) => (b.onclick = async () => { try { const r = await api(`/api/keys/${b.dataset.test}/test`, { method: "POST" }); toast(r.message, !r.ok); } catch (e) { toast(e.message, true); } }));
  $("#liveOn") && ($("#liveOn").onclick = async () => {
    if (!(await confirmBox("开启实盘模式？", "开启后，自动交易产生的调仓会尝试向交易所发送<b>真实订单</b>（仍需启动时设置 QTW_ALLOW_LIVE_ORDERS=1）。确定继续？", "我已了解风险，开启", true))) return;
    try { await api("/api/live", { method: "PUT", body: { mode: "live", live_enabled: true, confirm_phrase: $("#livePhrase").value.trim() } }); toast("实盘模式已开启"); await refreshStatus(); pageSettings(); } catch (e) { toast(e.message, true); }
  });
  $("#liveOff") && ($("#liveOff").onclick = async () => { await api("/api/live", { method: "PUT", body: { mode: "paper", live_enabled: false } }); toast("已回到纸面模式"); await refreshStatus(); pageSettings(); });
}

/* ---------- 帮助 ---------- */
function pageHelp() {
  const st = S.status.settings, s = st.strategy;
  $("#page").innerHTML = `<div class="fit fit-scroll"><div class="panel help">
  <section class="lead"><h4 style="margin-top:0">这是什么</h4><p>面向 kean 的系统化加密货币交易控制台：只用 OKX / Gate.io 官方<b>公共</b>行情（<b>无需 API Key</b>）做信号、回测与纸面交易；配置密钥后可在严格闸门下接入实盘。所有价格都来自交易所实时接口，<b>不使用任何模拟 / 伪造数据</b>，请求失败会直接报错。<b>这是系统化纸面 / 研究工具，不构成投资建议；实盘交易可能亏损全部本金。</b></p></section>
  <section><h4>顶部栏</h4><ul><li><b>纸面模式 / 实盘已开启</b>：当前交易模式，点击查看运行状态。</li><li><b>实时 · OKX</b>：行情连接状态（实时 / 部分重连 / 恢复中 / REST 兜底 / 数据延迟 / 中断），点击看每条连接。</li><li><b>行情源 OKX | Gate</b>：只切换公共行情来源，始终保持纸面。开启实盘只能在「设置」页完成。</li><li><b>跑一轮</b>：立即执行一次系统化周期（纸面调仓）。</li></ul></section>
  <section><h4>策略 · ${esc(s.rule_id)}</h4><ul>
  <li>现货与 USDT 永续<b>各自</b>在自己已收盘的 ${s.interval} K 线上计算 SMA${s.fast_ma} / SMA${s.slow_ma}；方向需连续 <b>${s.confirm_bars ?? 1}</b> 根已收盘 K 线一致才算有效信号。</li>
  <li>趋势过滤：${s.trend_ma ? `新开多仓需收盘价在 SMA${s.trend_ma} 之上、新开空仓需在其下，否则显示「逆趋势·暂缓」；已有持仓不受影响。` : "已关闭。"}</li>
  <li>空头熔断：${s.short_breaker_bars ? `同一规则的「只做空」影子账本在最近 ${s.short_breaker_bars} 根 K 线内已平仓合计亏损时，暂停新开空单，显示「空头熔断·暂缓」；转正后自动恢复，已有持仓不受影响。` : "已关闭。"}</li>
  <li>浮盈加仓（仅回测）：${s.pyramid_r ? `持仓前一根收盘浮盈 ≥ ${s.pyramid_r}×R（R = 入场价到止损的距离）时，下一根开盘加仓一次，规模 = ${s.pyramid_frac}× 原名义（受单币与总敞口上限约束），止损不动；模拟盘 / 实盘暂不执行。` : "已关闭。"}</li>
  <li>现货看多且永续不看空 → <b>做多·现货</b>；永续看空且现货不看多 → <b>做空·USDT 永续</b>（1 倍）；两者冲突或无信号 → 空仓。</li>
  <li>离场：收盘出现反向或归零信号，或价格触及 <b>${s.atr_stop_mult}×ATR${s.atr_period}</b> 止损；止损后等信号方向改变才再入场。</li></ul></section>
  <section><h4>仓位与风控</h4><ul><li>风险预算 = 权益 × ${pct(st.risk.max_risk_per_trade, 0)}；名义 = 风险预算 ÷ 止损百分比。4h 默认参数下止损距离通常只有几个百分点，名义会先被单币上限截住，所以实际单笔风险 ≈ 单币上限 × 止损距离（约 1% 权益）。</li><li>单币名义 ≤ 权益 × ${pct(st.risk.max_weight_per_name, 0)}；总敞口 ≤ 1× 权益，同时入场按比例缩放。</li><li>永续空头按 1 倍保证金占用现金；空头价格上涨时名义会超过权益，可用现金显示为负属正常记账，此时不会开新仓。</li></ul></section>
  <section><h4>页面</h4><ul><li><b>总览</b>：权益、现金 / 敞口 / 未实现、最近成交、回撤与胜率。</li><li><b>信号</b>：K 线实时图与每个币一行的信号列表（方向、标记价、建议仓位、止损、状态）；点击一行切换图表并打开进出场详情。</li><li><b>回测</b>：真实历史 K 线回测。</li><li><b>持仓</b>：纸面持仓，含入仓价、当前价与实时盈亏。</li><li><b>成交</b>：按开平配对的成交记录（进场价、出场价、单号、手续费、盈亏、原因）；持仓中的当前价与未实现盈亏随行情实时更新。</li><li><b>风控</b>：自动交易开关、紧急停止、参数与标的池。</li><li><b>设置</b>：行情源、加密密钥、实盘闸门。</li></ul></section>
  <section><h4>数据与时间</h4><ul><li>所有时间按 <b>Asia/Shanghai（北京时间）</b> 显示。</li><li>数据库：<code>data/qtw.sqlite</code>；API 密钥只存在加密文件 <code>data/secrets.enc</code>。</li><li>CSV 导出：<code>output/</code> 与 <code>output/backtest/</code>。图表：TradingView Lightweight Charts™。</li></ul></section>
  <section><h4>局限</h4><ul><li>回测未计资金费率与滑点；历史表现不代表未来。</li><li>实盘模式没有与交易所持仓对账；实盘前请先在 OKX 模拟盘 / Gate 合约测试网验证。</li><li>按 <code>Esc</code> 关闭弹窗 / 右侧抽屉。</li></ul></section></div>`;
}

/* ---------- 实时推送（SSE：后端订阅 OKX / Gate 官方公共 WebSocket） ---------- */
function applyForming() {
  const c = S.chart, L = S.live; if (!c || !L || !c._candle || !document.body.contains($("#candleChart"))) return;
  if (L.venue !== S.status.settings.venue) return;
  const f = L.forming[`${L.interval}:${c._sym}:${c._mkt}`];
  if (!f) return;
  const lastClosed = c._lastClosed || 0;
  // 未收盘 K 线会把 c._last 推到当前根。收盘检测必须对照「最后一根已收盘」时间，
  // 否则新周期开始时 f.time === c._last + iv，均线与交叉标记不会刷新。
  if (f.time > lastClosed + (c._iv || 0) && Date.now() - (c._loadedAt || 0) > 20000) {
    c._loadedAt = Date.now(); // 先打戳，避免 SSE 连续触发重复拉取
    loadCandles();
    refreshSignalsNow();
    return;
  }
  if (f.time >= (c._last || 0)) {
    try { c._candle.update({ time: f.time, open: f.open, high: f.high, low: f.low, close: f.close }); c._last = f.time; c._liveAt = Date.now(); c._liveKind = /_ws$/.test(f.source || "") ? "WebSocket" : "REST"; } catch (_) {}
  }
  renderChartSrc();
}
async function refreshSignalsNow() {
  if (S._sigRefreshing) return;
  S._sigRefreshing = true;
  try {
    S.signals = await api("/api/signals");
    renderRight();
    if (S.page === "signals") renderSigGrid();
  } catch (_) {}
  finally { S._sigRefreshing = false; }
}
/* 行情状态：实时 / 部分重连 / 恢复中 / REST 兜底 / 数据延迟 / 中断 */
function liveState() {
  const L = S.live, st = S.status;
  const src = L ? { mode: L.stream.mode, conns: L.connections, venue: L.venue, n: L.stream.quotes_ws_fresh, rest: L.stream.quotes_rest_fresh, unreachable: L.stream.unreachable, hint: L.stream.hint }
    : st && st.stream ? { mode: st.stream.mode, conns: st.stream.connections, venue: st.settings.venue, n: st.stream.quotes_ws_fresh, rest: st.stream.quotes_rest_fresh, unreachable: st.stream.unreachable, hint: st.stream.hint } : null;
  if (!src) return ["wait", "行情连接中…"];
  const V = VN[src.venue] || src.venue;
  if (S.esDown) return ["warn", `重连中 · ${V}`];
  if (L && S.liveAt && Date.now() - S.liveAt > 30000) return ["bad", `数据延迟 · ${Math.round((Date.now() - S.liveAt) / 1000)} 秒无更新`];
  // Only judge the selected venue's sockets — Gate being stale must not flash「无响应」on OKX (and vice versa).
  const mine = (src.conns || []).filter((c) => c.name && c.name.startsWith(src.venue));
  if (mine.some((c) => c.status === "stale")) return ["warn", `连接无响应 · ${V}`];
  if (src.mode === "ws") return mine.length && mine.every((c) => c.status === "connected") ? ["ok", `实时 · ${V}`] : ["warn", `实时 · ${V} 部分重连`];
  // WS sockets reconnecting / quote gap filled by REST — not a full REST-only fallback
  if (src.mode === "recovering") return ["warn", `恢复中 · ${V}`];
  if (src.unreachable || (src.mode === "down" && !src.n && !src.rest)) return ["bad", `${V} 不可达`];
  if (src.mode === "rest") return ["warn", `REST 兜底 · ${V}`];
  return ["bad", `行情中断 · ${V}`];
}
function renderLivePill() {
  const el = $("#livePill"); if (!el) return;
  const [c, txt] = liveState();
  el.className = "stat-pill " + c; el.querySelector("span").textContent = txt;
}
function applyLive() {
  const L = S.live; if (!L) return;
  renderLivePill();
  if (S.dash && L.paper) {
    Object.assign(S.dash, { equity: L.paper.equity, unrealized: L.paper.unrealized, gross: L.paper.gross, net: L.paper.net,
      total_pnl: L.paper.total_pnl, total_return: L.paper.total_pnl / S.dash.starting_equity });
    S.dash.cash_free = Math.abs(L.paper.equity - L.paper.gross) < 0.005 ? 0 : L.paper.equity - L.paper.gross;
    const syms = [];
    S.dash.positions.forEach((p) => {
      const q = L.paper.positions[p.symbol];
      if (q) Object.assign(p, { mark_price: q.mark, mark_time: q.mark_time, upnl: q.upnl, upnl_pct: q.upnl_pct, weight: q.weight, notional: q.notional, entry_price: q.entry != null ? q.entry : p.entry_price });
      syms.push(p.symbol);
    });
    const sig = syms.join();
    if (sig !== S._posSig) { S._posSig = sig; renderRight(); if (S.page === "positions") renderPosTable(); if (S.page === "trades") renderTradesPage(false); }
  }
  if (S.signals && L.venue === S.status?.settings.venue) S.signals.rows.forEach((r) => { const q = L.prices[r.symbol]; const m = r.market === "-" ? "spot" : r.market; if (q && q[m] && quoteFresh(q[m])) r.ref_price = q[m].price; });
  updateLiveCells();
  applyForming();
  applyMarkCandles();
  const now = Date.now();
  if (S.page === "dashboard" && now - (S._lastLiveRender || 0) > 5000 && !$("#modal:not(.hidden)") && !document.querySelector("#page :hover:is(button,a)")) {
    S._lastLiveRender = now; pageDashboard();
  }
}
// 止损距现价/开仓价与触发止损时的最大亏损（U），按方向计算；无止损时不显示。
function stopRisk(p) {
  const e = +p.entry_price, st = +p.stop_price, q = Math.abs(+p.qty);
  if (!(e > 0 && st > 0 && q > 0)) return "";
  const loss = (p.side === "short" ? st - e : e - st) * q;
  const dist = Math.abs(st - e) / e;
  return `<br><small class="muted" title="开仓价到止损价的距离；触发止损时这笔最多亏的金额">距 ${pct(dist, 1)} · 最多亏 ${f2(Math.max(loss, 0))} U</small>`;
}
function markCandleText(sym) {
  const m = S.live && S.live.mark_candles && S.live.mark_candles[sym];
  if (!m) return "—";
  const st = m.closed ? "已收盘" : "进行中";
  return `${fp(m.close)} · ${st}（仅展示，不参与信号）`;
}
function markCandleLine(sym) {
  const has = S.live && S.live.mark_candles && S.live.mark_candles[sym];
  if (!has && (S.status?.settings?.venue !== "okx")) return "";
  return `<p><i>标记价K线</i><span data-mark-candle="${sym}">${markCandleText(sym)}</span></p>`;
}
function applyMarkCandles() {
  document.querySelectorAll("[data-mark-candle]").forEach((el) => {
    el.textContent = markCandleText(el.dataset.markCandle);
  });
}
function connectLive() {
  try {
    const es = new EventSource("/api/stream");
    es.addEventListener("tick", (e) => { try { S.live = JSON.parse(e.data); S.liveAt = Date.now(); S.esDown = false; applyLive(); } catch (_) {} });
    es.onopen = () => { S.esDown = false; renderLivePill(); };
    es.onerror = () => { S.esDown = true; renderLivePill(); };
  } catch (_) {}
}
$("#livePill").onclick = () => {
  const L = S.live, conns = L ? L.connections : S.status?.stream?.connections || [], sm = L ? L.stream : S.status?.stream || {};
  modal(`<h3>实时行情连接</h3><div class="note" style="margin-bottom:8px">官方公共接口，无需 API Key。当前行情源：<b>${VN[S.status.settings.venue]}</b></div>${sm.hint ? `<div class="note ${sm.unreachable ? "neg" : ""}" style="margin-bottom:8px">${esc(sm.hint)}</div>` : ""}<div class="conn-list">${conns.map((c) => { const lab = ({connected:"已连接",connecting:"连接中",reconnecting:"重连中",stale:"无响应",stopped:"已停止",disabled:"已关闭"})[c.status] || c.status; const ok = c.status === "connected"; return `<div><b class="${ok ? "ok" : "bad"}">●</b> ${esc(c.name)} · ${esc(lab)}${c.last_msg ? ` · 最后消息 ${tFull(c.last_msg, true)}` : ""}${c.last_msg_age_sec != null ? `（${Math.round(c.last_msg_age_sec)} 秒前）` : ""}${c.reconnects ? ` · 累计重连 ${c.reconnects} 次` : ""}<br><span class="src">${esc(c.url)}</span>${c.last_error ? `<br><span class="src neg">${esc(c.last_error)}</span>` : ""}</div>`; }).join("") || "暂无连接信息"}</div>
   <div class="note" style="margin-top:10px">模式 ${sm.mode ?? "—"} · 当前行情源 WebSocket 新鲜报价 ${sm.quotes_ws_fresh ?? "—"} 个 · REST 兜底 ${sm.quotes_rest_fresh ?? "—"} 个。价格超过 20 秒无 WS 更新时自动改用官方 REST；重连窗口内标为「恢复中」而非误报 REST；已连接但长时间无消息标为「无响应」；获取失败只报错，不会编造价格。国内访问 OKX 失败时请配置 HTTPS_PROXY 或 QTW_PROXY 后重启。${sm.host_freeze_count ? `<br><span class="muted">本机曾暂停 ${sm.host_freeze_count} 次（最近一次约 ${Math.round(sm.last_host_freeze_gap_sec || 0)} 秒，${sm.last_host_freeze_age_sec != null ? Math.round(sm.last_host_freeze_age_sec / 60) + " 分钟前" : "—"}）；恢复后已自动重连并补齐价格，这不是行情故障。</span>` : ""}${Object.keys(sm.rest_errors || {}).length ? "<br><span class='neg'>REST 错误：" + Object.entries(sm.rest_errors).slice(0, 4).map(([k, v]) => esc(k + " " + v)).join("；") + "</span>" : ""}</div>
   <div class="acts"><button class="btn" data-close>关闭</button></div>`, (m) => (m.querySelector("[data-close]").onclick = closeModal));
};

/* ---------- 路由与刷新 ---------- */
const PAGES = { dashboard: pageDashboard, signals: pageSignals, backtest: pageBacktest, positions: pagePositions, trades: pageTrades, risk: pageRisk, settings: pageSettings, help: pageHelp };
const SUBS = { dashboard: "系统化纸面 / 研究工具 · 不构成投资建议", signals: "实时 K 线与每个币的进出场建议", backtest: "真实公共历史 K 线 · 无前视回测", positions: "持久化纸面持仓", trades: "开平配对的成交记录", risk: "自动交易、紧急停止与风控参数", settings: "行情源、API 密钥（加密保存）与实盘闸门", help: "使用说明与风险提示" };
async function refreshStatus() { S.status = await api("/api/status"); renderMode(); }
async function refreshDash() { S.dash = await api("/api/dashboard"); }
async function refreshAll() {
  try { await Promise.all([refreshStatus(), refreshDash()]); } catch (e) { toast("无法连接后端：" + e.message, true); return; }
  renderRight();
  if (["dashboard", "positions"].includes(S.page)) PAGES[S.page]();
}
async function route() {
  S.page = (location.hash.replace("#/", "") || "dashboard").split("?")[0];
  if (!PAGES[S.page]) S.page = "dashboard";
  if (S.page !== "signals") S.chart = null;
  renderNav(); renderTitle();
  if (!S.status || !S.dash) await refreshAll();
  try { await PAGES[S.page](); } catch (e) { $("#page").innerHTML = `<div class="empty neg">${esc(e.message)}</div>`; }
  $("#page").scrollTop = 0;
}
function renderDashTx() { /* 总览成交预览本身只取前几条，高度由网格约束 */ }
function renderBtTrades() {
  const host = $("#btTrades"); if (!host || !S.bt || !S.bt.trades) return;
  const rows = S.bt.trades.slice().reverse();
  if (!host.querySelector("table")) {
    host.innerHTML = `<table class="tbl"><thead><tr><th>标的</th><th>方向</th><th>入场时间</th><th>入场价</th><th>离场时间</th><th>离场价</th><th>名义</th><th>盈亏</th><th>收益率</th><th>持有根数</th><th>离场原因</th></tr></thead><tbody></tbody></table>`;
  }
  const st = pgState("btTrades", rows.length, fitRows(host, 36, 28, 2));
  const slice = rows.slice(st.start, st.end);
  const body = host.querySelector("tbody");
  body.innerHTML = slice.map((x) => `<tr><td><b>${esc(x.symbol)}</b></td><td><span class="pill ${x.side}">${sideCn(x.side)} · ${mktCn(x.market)}</span></td><td>${tFull(x.entry_time)}</td><td class="num">${fp(x.entry_price)}</td><td>${x.exit_time ? tFull(x.exit_time) : "—"}</td><td class="num">${fp(x.exit_price)}</td><td class="num">${f2(x.notional_usdt)}</td><td class="num ${cls(x.pnl_usdt)}">${sgn(x.pnl_usdt)}</td><td class="num ${cls(x.return_pct)}">${pct(x.return_pct)}</td><td class="num">${x.bars_held}</td><td title="${esc(x.exit_reason || "")}">${esc(x.exit_reason)}</td></tr>`).join("");
  const pg = $("#btPager"); if (pg) { pg.innerHTML = pagerHtml("btTrades", st); bindPager("btTrades", renderBtTrades); }
  requestAnimationFrame(() => refitByActualRows(host, "btTrades", "tbody tr", renderBtTrades, 1));
  clearTimeout(S._btFitT);
  S._btFitT = setTimeout(() => refitByActualRows(host, "btTrades", "tbody tr", renderBtTrades, 1), 180);
}
window.addEventListener("hashchange", route);
greet(); setInterval(greet, 60000);
hydrateIcons();
route().then(() => api("/api/signals").then((r) => { S.signals = r; renderRight(); if (S.page === "dashboard") pageDashboard(); }).catch(() => {}));
if (!new URLSearchParams(location.search).has("nolive")) connectLive(); // nolive 仅用于无头截图
setInterval(renderLivePill, 5000);
setInterval(() => { if (S.page === "signals") renderChartSrc(); }, 1000);
setInterval(async () => { await refreshAll(); }, 30000);
setInterval(() => { refreshSignalsNow(); }, 120000);
window.addEventListener("resize", () => { clearTimeout(S._fitT); S._fitT = setTimeout(relayoutPagers, 120); });
if (window.ResizeObserver) {
  const ro = new ResizeObserver(() => { clearTimeout(S._fitT); S._fitT = setTimeout(relayoutPagers, 120); });
  const hook = () => { const el = $("#page"); if (el && el !== S._fitEl) { if (S._fitEl) ro.unobserve(S._fitEl); ro.observe(el); S._fitEl = el; } };
  hook(); setInterval(hook, 2000);
}
